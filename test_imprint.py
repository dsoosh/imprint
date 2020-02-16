import inspect

import pytest

from imprint import hardcode, hardcode_parametrized


def test_add_mark_to_test_without_one(testdir):
    before = """
        def test_without_mark():
            pass
    """

    after = """
        @pytest.mark.testcaseid(12345)
        def test_without_mark():
            pass
    """

    item_before = testdir.getitem(source=before, funcname="test_without_mark")
    decorated = hardcode(item_before, pytest.mark.testcaseid(12345))

    item_after = testdir.getitem(source=after, funcname="test_without_mark")

    assert decorated == inspect.getsource(item_after.function)


def test_dont_add_mark_to_test_that_already_has_one(testdir):
    before = after = """
        import pytest
        @pytest.mark.testcaseid(12345)
        def test_with_mark():
            pass
    """

    item_before = testdir.getitem(source=before, funcname="test_with_mark")
    decorated = hardcode(item_before, pytest.mark.testcaseid(12345))

    item_after = testdir.getitem(source=after, funcname="test_with_mark")

    assert decorated == inspect.getsource(item_after.function)


def test_decorate_parametrized_test(testdir):
    before = """
        import pytest
        @pytest.mark.parametrize("value", [1, 2, 3])
        def test_parametrized(value):
            assert isinstance(value, int)
    """
    after = """
        import pytest
        @pytest.mark.parametrize("value", (
            pytest.param(1, marks=[pytest.mark.testcaseid(11111)]),
            pytest.param(2, marks=[]),
            pytest.param(3, marks=[]),
        ))
        def test_parametrized(value):
            assert isinstance(value, int)
    """

    item_before = testdir.getitem(source=before, funcname="test_parametrized[1]")

    decorated = hardcode_parametrized({item_before: [pytest.mark.testcaseid(11111)]})

    item_after = testdir.getitem(source=after, funcname="test_parametrized[1]")

    assert decorated == inspect.getsource(item_after.function)


def test_decorate_parametrized_test_two_values(testdir):
    before = """
        import pytest
        @pytest.mark.parametrize("value", [1, 2, 3])
        def test_parametrized(value):
            assert isinstance(value, int)
    """
    after = """
        import pytest
        @pytest.mark.parametrize("value", (
            pytest.param(1, marks=[pytest.mark.testcaseid(11111)]),
            pytest.param(2, marks=[]),
            pytest.param(3, marks=[pytest.mark.testcaseid(33333)]),
        ))
        def test_parametrized(value):
            assert isinstance(value, int)
    """

    first = testdir.getitem(source=before, funcname="test_parametrized[1]")
    third = testdir.getitem(source=before, funcname="test_parametrized[3]")

    decorated = hardcode_parametrized({
        first: [pytest.mark.testcaseid(11111)],
        third: [pytest.mark.testcaseid(33333)],
    })

    item_after = testdir.getitem(source=after, funcname="test_parametrized[1]")

    assert decorated == inspect.getsource(item_after.function)
