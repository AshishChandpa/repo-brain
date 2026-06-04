from repo_brain.parsers.pytest import is_test_file, parse_tests

TEST_SOURCE = """
import pytest

def test_something():
    assert 1 == 1

async def test_async_thing():
    pass

def helper():
    pass

class TestMyFeature:
    def test_works(self):
        pass

    def not_a_test(self):
        pass

class NotATestClass:
    def test_inside_non_test_class(self):
        pass
"""


def test_is_test_file_prefix():
    assert is_test_file("test_scanner.py") is True


def test_is_test_file_suffix():
    assert is_test_file("scanner_test.py") is True


def test_is_not_test_file():
    assert is_test_file("scanner.py") is False
    assert is_test_file("routes.py") is False


def test_detects_test_functions():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "test_something" in info.test_functions
    assert "test_async_thing" in info.test_functions


def test_detects_test_class():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "TestMyFeature" in info.test_classes


def test_detects_methods_in_test_class():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "TestMyFeature.test_works" in info.test_functions


def test_ignores_helper_function():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "helper" not in info.test_functions


def test_ignores_non_test_class():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "NotATestClass" not in info.test_classes


def test_syntax_error_returns_empty():
    info = parse_tests("bad.py", "def (broken:")
    assert info.test_functions == []
    assert info.test_classes == []
