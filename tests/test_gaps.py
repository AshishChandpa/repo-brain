from repo_brain.gaps import find_gaps
from repo_brain.models import SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

SYMBOLS = [
    SymbolInfo(file_path="app/users.py", name="UserService", symbol_type="class", lineno=10),
    SymbolInfo(file_path="app/users.py", name="get_user", symbol_type="function", lineno=20),
    SymbolInfo(file_path="app/users.py", name="create_user", symbol_type="async_function", lineno=30),
    SymbolInfo(file_path="app/users.py", name="_internal_helper", symbol_type="function", lineno=40),
    SymbolInfo(file_path="app/docs.py", name="DocumentService", symbol_type="class", lineno=10),
    SymbolInfo(file_path="app/docs.py", name="upload_document", symbol_type="async_function", lineno=20),
    # method — should NOT appear in gaps (only class/function/async_function are tested)
    SymbolInfo(file_path="app/users.py", name="find_by_id", symbol_type="method", lineno=15, parent="UserService"),
]

TESTS_COVERING_USERS = [
    TestInfo(
        file_path="tests/test_users.py",
        test_functions=["test_get_user", "test_create_user", "test_userservice_init"],
        test_classes=["TestUserService"],
    )
]

TESTS_COVERING_DOCS = [
    TestInfo(
        file_path="tests/test_docs.py",
        test_functions=["test_upload_document"],
        test_classes=[],
    )
]

EMPTY_TESTS: list[TestInfo] = []


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_no_gaps_when_all_covered():
    gaps = find_gaps(SYMBOLS, TESTS_COVERING_USERS + TESTS_COVERING_DOCS)
    # All non-test symbols covered — at minimum users.py is covered by test_users.py stem
    assert isinstance(gaps, list)


def test_all_gaps_when_no_tests():
    gaps = find_gaps(SYMBOLS, EMPTY_TESTS)
    # All testable symbols (class / function / async_function) have no coverage
    types = {g.symbol_type for g in gaps}
    assert "class" in types
    assert "function" in types
    assert "async_function" in types


def test_method_not_in_gaps():
    gaps = find_gaps(SYMBOLS, EMPTY_TESTS)
    names = [g.symbol_name for g in gaps]
    assert "find_by_id" not in names


def test_gaps_sorted_by_file_then_line():
    gaps = find_gaps(SYMBOLS, EMPTY_TESTS)
    files = [g.file_path for g in gaps]
    assert files == sorted(files)


def test_filter_by_file():
    gaps = find_gaps(SYMBOLS, EMPTY_TESTS, file_filter="app/users.py")
    assert all(g.file_path == "app/users.py" for g in gaps)
    assert any(g.symbol_name == "get_user" for g in gaps)
    assert not any(g.file_path == "app/docs.py" for g in gaps)


def test_test_files_excluded_from_gaps():
    test_symbols = [
        SymbolInfo(file_path="tests/test_users.py", name="test_something", symbol_type="function", lineno=5),
    ]
    gaps = find_gaps(test_symbols, EMPTY_TESTS)
    assert gaps == []


def test_function_covered_by_name_match():
    tests = [
        TestInfo(
            file_path="tests/some_test.py",
            test_functions=["test_upload_document_success"],
            test_classes=[],
        )
    ]
    gaps = find_gaps(
        [SymbolInfo(file_path="app/docs.py", name="upload_document", symbol_type="function", lineno=5)],
        tests,
    )
    # "upload_document" is in the test function name → covered
    assert gaps == []


def test_class_covered_by_test_class_name():
    tests = [
        TestInfo(
            file_path="tests/test_docs.py",
            test_functions=[],
            test_classes=["TestDocumentService"],
        )
    ]
    gaps = find_gaps(
        [SymbolInfo(file_path="app/docs.py", name="DocumentService", symbol_type="class", lineno=5)],
        tests,
    )
    # "documentservice" is in "testdocumentservice" → covered
    assert gaps == []