from __future__ import annotations

import re

from repo_brain.models import ImportInfo, RouteInfo, SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}

# Single import: import "pkg"
_IMPORT_SINGLE_RE = re.compile(r'^\s*import\s+"([^"]+)"', re.MULTILINE)

# Group import: import ( "pkg" \n "pkg2" )
_IMPORT_GROUP_RE = re.compile(r'import\s*\(([^)]+)\)', re.DOTALL)
_IMPORT_LINE_RE = re.compile(r'(?:(\w+)\s+)?"([^"]+)"')

# Function: func Name( or func (recv) Name(
_FUNC_RE = re.compile(
    r"^func\s+(?:\(\s*\w+\s+\*?\w+\s*\)\s+)?(\w+)\s*\(",
    re.MULTILINE,
)

# Struct: type Foo struct
_STRUCT_RE = re.compile(r"^type\s+(\w+)\s+struct\b", re.MULTILINE)

# Interface: type Foo interface
_INTERFACE_RE = re.compile(r"^type\s+(\w+)\s+interface\b", re.MULTILINE)

# chi:       r.Get("/path", handler) or r.Method("GET", "/path", handler)
# gin:       r.GET("/path", handler) or group.POST("/path", handler)
# echo:      e.GET("/path", handler)
# net/http:  http.HandleFunc("/path", handler) or mux.HandleFunc("/path", handler)
_ROUTE_PATTERNS = [
    # chi / gorilla mux / httprouter style: r.Get("/path",
    re.compile(
        r'\b(?:r|router|mux|group|v\d+?)\s*\.\s*'
        r'(Get|Post|Put|Patch|Delete|Options|Head|All)\s*\(\s*"([^"]+)"',
        re.IGNORECASE,
    ),
    # gin / echo style: r.GET("/path",
    re.compile(
        r'\b(?:r|router|engine|e|g|api|v\d+?)\s*\.\s*'
        r'(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s*\(\s*"([^"]+)"',
    ),
    # net/http: http.HandleFunc("/path", or mux.HandleFunc("/path",
    re.compile(
        r'\b(?:http\.HandleFunc|mux\.HandleFunc|http\.Handle)\s*\(\s*"([^"]+)"',
    ),
]

# Test function: func TestXxx(t *testing.T) or func TestXxx(b *testing.B)
_TEST_FUNC_RE = re.compile(
    r"^func\s+(Test\w+|Benchmark\w+|Example\w+)\s*\(\w+\s+\*testing\.",
    re.MULTILINE,
)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def is_test_file(path: str) -> bool:
    return path.endswith("_test.go")


def parse_imports(file_path: str, source: str) -> list[ImportInfo]:
    results: list[ImportInfo] = []

    for m in _IMPORT_SINGLE_RE.finditer(source):
        results.append(ImportInfo(file_path=file_path, module=m.group(1), level=0))

    for block in _IMPORT_GROUP_RE.finditer(source):
        for m in _IMPORT_LINE_RE.finditer(block.group(1)):
            alias, module = m.group(1), m.group(2)
            results.append(ImportInfo(
                file_path=file_path, module=module,
                alias=alias if alias else None, level=0,
            ))

    return results


def parse_symbols(file_path: str, source: str) -> list[SymbolInfo]:
    results: list[SymbolInfo] = []

    for m in _STRUCT_RE.finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        results.append(SymbolInfo(
            file_path=file_path, name=m.group(1),
            symbol_type="struct", lineno=lineno,
        ))

    for m in _INTERFACE_RE.finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        results.append(SymbolInfo(
            file_path=file_path, name=m.group(1),
            symbol_type="interface", lineno=lineno,
        ))

    for m in _FUNC_RE.finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        results.append(SymbolInfo(
            file_path=file_path, name=m.group(1),
            symbol_type="function", lineno=lineno,
        ))

    return results


def parse_routes(file_path: str, source: str) -> list[RouteInfo]:
    results: list[RouteInfo] = []

    for pattern in _ROUTE_PATTERNS[:2]:
        for m in pattern.finditer(source):
            method, path = m.group(1).lower(), m.group(2)
            lineno = source[: m.start()].count("\n") + 1
            results.append(RouteInfo(
                file_path=file_path, method=method, path=path,
                function_name="", lineno=lineno,
            ))

    # net/http pattern has only one capture group (path)
    for m in _ROUTE_PATTERNS[2].finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        results.append(RouteInfo(
            file_path=file_path, method="handle", path=m.group(1),
            function_name="", lineno=lineno,
        ))

    return results


def parse_tests(file_path: str, source: str) -> TestInfo:
    test_functions = [m.group(1) for m in _TEST_FUNC_RE.finditer(source)]
    return TestInfo(
        file_path=file_path,
        test_functions=test_functions,
        test_classes=[],
    )