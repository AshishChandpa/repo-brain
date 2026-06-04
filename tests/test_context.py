import pytest

from repo_brain.context import (
    _extract_keywords,
    _match_routes,
    _match_tests,
    _score_files,
    _score_symbols,
    _tokenize_path,
    build_context,
)
from repo_brain.models import ImportInfo, RouteInfo, SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

SYMBOLS = [
    SymbolInfo(file_path="app/services/document_service.py", name="DocumentService", symbol_type="class", lineno=5),
    SymbolInfo(file_path="app/services/document_service.py", name="upload_document", symbol_type="function", lineno=20),
    SymbolInfo(file_path="app/services/audit_log.py", name="AuditLog", symbol_type="class", lineno=3),
    SymbolInfo(file_path="app/services/audit_log.py", name="write_audit_entry", symbol_type="function", lineno=15),
    SymbolInfo(file_path="app/models/user.py", name="User", symbol_type="class", lineno=1),
    SymbolInfo(file_path="app/utils/helpers.py", name="format_date", symbol_type="function", lineno=8),
]

ROUTES = [
    RouteInfo(file_path="app/routes/documents.py", method="post", path="/documents/upload", function_name="upload_document", lineno=10),
    RouteInfo(file_path="app/routes/documents.py", method="get", path="/documents/{doc_id}", function_name="get_document", lineno=20),
    RouteInfo(file_path="app/routes/users.py", method="get", path="/users", function_name="list_users", lineno=5),
]

IMPORTS = [
    ImportInfo(file_path="app/routes/documents.py", module="app.services.document_service", level=0),
    ImportInfo(file_path="app/routes/users.py", module="app.models.user", level=0),
]

TESTS = [
    TestInfo(file_path="tests/test_document_service.py", test_functions=["test_upload_document", "test_get_document"], test_classes=[]),
    TestInfo(file_path="tests/test_audit_log.py", test_functions=["test_write_audit_entry"], test_classes=[]),
    TestInfo(file_path="tests/test_users.py", test_functions=["test_list_users"], test_classes=[]),
]


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------

def test_keywords_lowercased():
    kws = _extract_keywords("Add Audit Logging")
    assert all(k == k.lower() for k in kws)

def test_keywords_removes_stopwords():
    kws = _extract_keywords("add audit logging to document upload")
    assert "add" not in kws
    assert "to" not in kws
    assert "audit" in kws
    assert "logging" in kws
    assert "document" in kws
    assert "upload" in kws

def test_keywords_splits_camelcase():
    kws = _extract_keywords("documentUpload auditLog")
    assert "document" in kws
    assert "upload" in kws
    assert "audit" in kws
    assert "log" in kws

def test_keywords_splits_underscores():
    kws = _extract_keywords("document_service audit_log")
    assert "document" in kws
    assert "service" in kws
    assert "audit" in kws

def test_keywords_deduplicates():
    kws = _extract_keywords("audit audit log audit")
    assert kws.count("audit") == 1

def test_keywords_empty_task():
    assert _extract_keywords("") == []

def test_keywords_all_stopwords():
    kws = _extract_keywords("add fix get set")
    assert kws == []


# ---------------------------------------------------------------------------
# _tokenize_path — regression tests for edge cases that crashed on Python 3.12+
# ---------------------------------------------------------------------------

def test_tokenize_root_route():
    # Path("/").with_suffix("") raised ValueError in Python 3.12+ (empty stem)
    assert _tokenize_path("/") == []

def test_tokenize_route_with_path_param():
    tokens = _tokenize_path("/documents/{doc_id}")
    assert "documents" in tokens
    assert "doc" in tokens
    assert "id" in tokens

def test_tokenize_route_with_dotted_param():
    # e.g. /items/{item.id} — dot inside curly braces
    tokens = _tokenize_path("/items/{item.id}")
    assert "items" in tokens

def test_tokenize_file_path_strips_py():
    tokens = _tokenize_path("app/services/document_service.py")
    assert "py" not in tokens
    assert "document" in tokens
    assert "service" in tokens

def test_tokenize_camelcase():
    tokens = _tokenize_path("DocumentService")
    assert "document" in tokens
    assert "service" in tokens

def test_tokenize_empty_string():
    assert _tokenize_path("") == []

def test_tokenize_plain_function_name():
    tokens = _tokenize_path("upload_document")
    assert "upload" in tokens
    assert "document" in tokens


# ---------------------------------------------------------------------------
# _score_files
# ---------------------------------------------------------------------------

def test_score_files_matches_relevant():
    files = [
        "app/services/document_service.py",
        "app/services/audit_log.py",
        "app/models/user.py",
    ]
    scored = _score_files(files, ["document", "upload"])
    paths = [s.path for s in scored]
    assert "app/services/document_service.py" in paths

def test_score_files_excludes_unrelated():
    files = ["app/models/user.py", "app/utils/helpers.py"]
    scored = _score_files(files, ["document", "upload"])
    assert scored == []

def test_score_files_sorted_by_score():
    files = [
        "app/services/audit_log.py",
        "app/audit/audit_document_log.py",
    ]
    scored = _score_files(files, ["audit", "document"])
    assert scored[0].score >= scored[-1].score

def test_score_files_score_positive():
    files = ["app/services/document_service.py"]
    scored = _score_files(files, ["document"])
    assert scored[0].score > 0


# ---------------------------------------------------------------------------
# _score_symbols
# ---------------------------------------------------------------------------

def test_score_symbols_matches_name():
    scored = _score_symbols(SYMBOLS, ["document", "upload"])
    names = [s.symbol.name for s in scored]
    assert "upload_document" in names
    assert "DocumentService" in names

def test_score_symbols_excludes_unrelated():
    scored = _score_symbols(SYMBOLS, ["document", "upload"])
    names = [s.symbol.name for s in scored]
    assert "format_date" not in names

def test_score_symbols_sorted_descending():
    scored = _score_symbols(SYMBOLS, ["audit", "log"])
    assert all(scored[i].score >= scored[i + 1].score for i in range(len(scored) - 1))


# ---------------------------------------------------------------------------
# _match_routes — including root route regression
# ---------------------------------------------------------------------------

def test_match_routes_by_path():
    matched = _match_routes(ROUTES, ["document", "upload"])
    paths = [r.path for r in matched]
    assert "/documents/upload" in paths

def test_match_routes_by_function():
    matched = _match_routes(ROUTES, ["upload"])
    assert any(r.function_name == "upload_document" for r in matched)

def test_match_routes_excludes_unrelated():
    matched = _match_routes(ROUTES, ["audit"])
    assert matched == []


def test_match_routes_root_path_does_not_crash():
    # Regression: Path("/").with_suffix("") raised ValueError in Python 3.12+
    root_route = RouteInfo(file_path="app/main.py", method="get", path="/", function_name="health", lineno=1)
    result = _match_routes([root_route], ["health"])
    assert isinstance(result, list)

def test_match_routes_path_param_does_not_crash():
    param_route = RouteInfo(file_path="app/routes.py", method="get", path="/items/{item_id}", function_name="get_item", lineno=1)
    result = _match_routes([param_route], ["items"])
    assert any(r.path == "/items/{item_id}" for r in result)


# ---------------------------------------------------------------------------
# _match_tests
# ---------------------------------------------------------------------------

def test_match_tests_by_filename():
    matched = _match_tests(TESTS, ["document"])
    assert "tests/test_document_service.py" in matched

def test_match_tests_by_function_name():
    matched = _match_tests(TESTS, ["audit"])
    assert "tests/test_audit_log.py" in matched

def test_match_tests_excludes_unrelated():
    matched = _match_tests(TESTS, ["document"])
    assert "tests/test_users.py" not in matched

def test_match_tests_sorted():
    matched = _match_tests(TESTS, ["document", "audit"])
    assert matched == sorted(matched)


# ---------------------------------------------------------------------------
# build_context (integration)
# ---------------------------------------------------------------------------

def test_build_context_returns_keywords():
    result = build_context("audit logging for document upload", SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "audit" in result.keywords
    assert "document" in result.keywords

def test_build_context_suggests_relevant_files():
    result = build_context("document upload service", SYMBOLS, ROUTES, IMPORTS, TESTS)
    paths = [f.path for f in result.suggested_files]
    assert any("document" in p for p in paths)

def test_build_context_suggests_relevant_symbols():
    result = build_context("audit log entry", SYMBOLS, ROUTES, IMPORTS, TESTS)
    names = [s.symbol.name for s in result.suggested_symbols]
    assert "AuditLog" in names or "write_audit_entry" in names

def test_build_context_suggests_routes():
    result = build_context("document upload", SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert any(r.path == "/documents/upload" for r in result.suggested_routes)

def test_build_context_suggests_tests():
    result = build_context("document upload", SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "tests/test_document_service.py" in result.suggested_tests

def test_build_context_empty_task():
    result = build_context("add fix get", SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert result.keywords == []
    assert result.suggested_files == []
    assert result.suggested_symbols == []

def test_build_context_caps_files_at_ten():
    many_files = [
        SymbolInfo(file_path=f"app/doc_module_{i}/service.py", name=f"DocService{i}", symbol_type="class", lineno=1)
        for i in range(20)
    ]
    result = build_context("doc module service", many_files, [], [], [])
    assert len(result.suggested_files) <= 10

def test_build_context_caps_symbols_at_ten():
    many_symbols = [
        SymbolInfo(file_path="app/doc.py", name=f"doc_function_{i}", symbol_type="function", lineno=i)
        for i in range(20)
    ]
    result = build_context("doc function", many_symbols, [], [], [])
    assert len(result.suggested_symbols) <= 10