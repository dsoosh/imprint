import inspect
import logging
import re
from collections import defaultdict, OrderedDict, Iterable
from pathlib import Path
from typing import List, Dict, Tuple

from _pytest.mark import Mark
from _pytest.python import Function

import pytest


class Collector:
    items = []

    def __init__(self, path: str):
        self.path = Path(path)

    def pytest_collection_modifyitems(self, items):
        self.items = list(filter(lambda item: self.path in Path(item.location[0]).parents, items))
        logging.info(f"collected {len(items)} under {self.path}")


def assign_marks_to_tests(marks: Dict[str, List[Mark]]):
    collector = Collector(".")
    pytest.main(args=[".", "--collect-only"], plugins=[collector])

    marks_for_parametrized_test = defaultdict(list)
    marks_for_test = {}
    for item in collector.items:
        test_marks = marks.get(item.name, [])
        if item.get_closest_marker("parametrize"):
            # group parametrized tests by test function to apply all marks
            # for pytest.mark.parametrized in one go
            marks_for_parametrized_test[item.function].append((item, test_marks))
        else:
            marks_for_test[item] = test_marks
    return marks_for_test, marks_for_parametrized_test


def decorate_parametrized_in_source(items: Dict[callable, Tuple[Function, List[Mark]]]):
    for func, its in items.items():
        sourcefile = inspect.getsourcefile(func)
        with open(sourcefile, "r") as source:
            src = source.read()

        decorated = hardcode_parametrized(dict(its))
        funcsource = inspect.getsource(func)
        src = src.replace(funcsource, decorated)

        with open(sourcefile, "w") as source:
            source.write(src)


def decorate_single(items: Dict[Function, List[Mark]]):
    for item, marks in items.items():
        if not marks:
            continue
        funcsource = inspect.getsource(item.function)

        decorated = hardcode(item, marks)

        sourcefile = inspect.getsourcefile(item.function)
        with open(sourcefile, "r") as source:
            src = source.read()

        replace = src.replace(funcsource, decorated)

        with open(sourcefile, "w") as source:
            source.write(replace)


if __name__ == '__main__':
    marks = {
        "test_parm2": [pytest.mark.testcaseid(12345)],
        "test_parm[2]": [pytest.mark.testcaseid(12346), pytest.mark.testcaseid(12)],
        "test_parm[1]": [pytest.mark.testcaseid(1)]
    }
    single, parametrized = assign_marks_to_tests(marks)
    decorate_single(single)
    decorate_parametrized_in_source(parametrized)


def hardcode(test: Function, marks: List[Mark]) -> str:
    source = inspect.getsource(test.function)
    if not isinstance(marks, Iterable):
        marks = [marks]

    for mark in marks:
        mark = getattr(mark, "mark", mark)  # unwrap MarkDecorator
        if mark in test.own_markers:
            continue
        formatted = "@" + _format_mark(mark)
        function_def = f"def {test.name}"
        source = source.replace(function_def, f"{formatted}\n{function_def}")
    return source


def hardcode_parametrized(tests: Dict[Function, List[Mark]]):
    first = next(iter(tests))
    assert all(test.function == first.function for test in tests), "Marked parametrized function differs"

    source = inspect.getsource(first.function)
    parametrized = first.get_closest_marker("parametrize")
    names, values = parametrized.args

    marks_for_value = OrderedDict((value, []) for value in values)

    for value in values:
        for test, marks in tests.items():
            if test.name == f"{test.originalname}[{value}]":
                marks_for_value[value].extend(marks)
                break

    formatted = f"@pytest.mark.parametrize(\"{names}\", (\n"
    for value, marks in marks_for_value.items():
        formatted += f"    pytest.param({value}, marks=[{_format_marks(marks)}]),\n"
    formatted += "))"

    return re.sub(pattern=r"@pytest\.mark\.parametrize\(.*?\)", string=source, repl=formatted)


def _format_mark(mark):
    args = f"({', '.join(map(str, mark.args))})" if mark.args else ""
    return f"pytest.mark.{mark.name}" + args


def _format_marks(marks):
    return ", ".join(map(_format_mark, marks))
