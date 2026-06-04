from repo_brain.impact import analyse, _module_variants, _to_module_path
from repo_brain.models import ImportInfo, RouteInfo, SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

SYMBOLS = [
    SymbolInfo(file_path="app/services/users.py", name="UserService", symbol_type="class", lineno=5),
    SymbolInfo(file_path="app/services/users.py", name="get_user", symbol_type="function", lineno=20),
    SymbolInfo(file_path="app/routes/items.py", name="list_items", symbol_type="function", lineno=10),
]

ROUTES = [
    RouteInfo(file_path="app/routes/users.py", method="get", path="/users", function_name="list_users", lineno=8),
    RouteInfo(file_path="app/services/users.py", method="post", path="/users", function_name="create_user", lineno=30),
]

IMPORTS = [
    ImportInfo(file_path="app/routes/users.py", module="app.services.users", level=0),
    ImportInfo(file_path="app/routes/items.py", module="services.users", level=0),
    ImportInfo(file_path="tests/test_users.py", module="app.services.users", level=0),
    ImportInfo(file_path="app/main.py", module="utils", level=0),
]

TESTS = [
    TestInfo(file_path="tests/test_users.py", test_functions=["test_get_user"], test_classes=[]),
    TestInfo(file_path="tests/test_items.py", test_functions=["test_list_items"], test_classes=[]),
]

TARGET = "app/services/users.py"


# ---------------------------------------------------------------------------
# _to_module_path
# ---------------------------------------------------------------------------

def test_module_path_simple():
    assert _to_module_path("app/services/users.py") == "app.services.users"

def test_module_path_init():
    assert _to_module_path("app/services/__init__.py") == "app.services"

def test_module_path_root():
    assert _to_module_path("main.py") == "main"

def test_module_path_non_py():
    assert _to_module_path("README.md") is None


# ---------------------------------------------------------------------------
# _module_variants
# ---------------------------------------------------------------------------

def test_module_variants():
    from pathlib import Path
    variants = _module_variants(Path("app/services/users.py"))
    assert "app.services.users" in variants
    assert "services.users" in variants
    assert "users" in variants

def test_module_variants_init():
    from pathlib import Path
    variants = _module_variants(Path("app/services/__init__.py"))
    assert "app.services" in variants
    assert "services" in variants


# ---------------------------------------------------------------------------
# analyse — symbols and routes in file
# ---------------------------------------------------------------------------

def test_symbols_in_target():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    names = [s.name for s in result.symbols]
    assert "UserService" in names
    assert "get_user" in names
    assert "list_items" not in names  # different file

def test_routes_in_target():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert any(r.path == "/users" and r.method == "post" for r in result.routes)
    # route from app/routes/users.py must NOT appear
    assert not any(r.file_path == "app/routes/users.py" for r in result.routes)


# ---------------------------------------------------------------------------
# analyse — imported_by
# ---------------------------------------------------------------------------

def test_imported_by_finds_importers():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "app/routes/users.py" in result.imported_by
    assert "app/routes/items.py" in result.imported_by

def test_imported_by_excludes_target_itself():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert TARGET not in result.imported_by

def test_imported_by_excludes_unrelated():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "app/main.py" not in result.imported_by


# ---------------------------------------------------------------------------
# analyse — related_tests
# ---------------------------------------------------------------------------

def test_related_tests_by_import():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "tests/test_users.py" in result.related_tests

def test_related_tests_by_name_heuristic():
    # test_users.py matches stem "users" even without import match
    imports_no_test = [i for i in IMPORTS if i.file_path != "tests/test_users.py"]
    result = analyse(TARGET, SYMBOLS, ROUTES, imports_no_test, TESTS)
    assert "tests/test_users.py" in result.related_tests

def test_unrelated_tests_excluded():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "tests/test_items.py" not in result.related_tests


# ---------------------------------------------------------------------------
# analyse — likely_affected
# ---------------------------------------------------------------------------

def test_likely_affected_union():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert "app/routes/users.py" in result.likely_affected
    assert "app/routes/items.py" in result.likely_affected
    assert "tests/test_users.py" in result.likely_affected

def test_likely_affected_excludes_target():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert TARGET not in result.likely_affected

def test_likely_affected_is_sorted():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert result.likely_affected == sorted(result.likely_affected)


# ---------------------------------------------------------------------------
# edge cases
# ---------------------------------------------------------------------------

def test_no_importers():
    result = analyse("app/isolated.py", SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert result.imported_by == []

def test_no_symbols_in_file():
    result = analyse("app/isolated.py", SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert result.symbols == []

def test_module_path_in_result():
    result = analyse(TARGET, SYMBOLS, ROUTES, IMPORTS, TESTS)
    assert result.module_path == "app.services.users"