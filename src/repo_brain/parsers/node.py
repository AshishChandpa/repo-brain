from __future__ import annotations

import re

from repo_brain.models import CallInfo, ImportInfo, RouteInfo, RouteLink, SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# constants
# ---------------------------------------------------------------------------

NODE_TEST_EXTENSIONS = {".test.js", ".spec.js", ".test.ts", ".spec.ts",
                        ".test.mjs", ".spec.mjs", ".test.cjs", ".spec.cjs"}

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "all", "use"}

# Express/Fastify/Hono/Koa route patterns: app.get('/path', ...) or router.post('/path')
_ROUTE_RE = re.compile(
    r"(?:app|router|server|fastify|r)\s*\.\s*"
    r"(get|post|put|patch|delete|options|head|all)\s*\(\s*['\"`]([^'\"`]+)['\"`]",
    re.IGNORECASE,
)

# ES module imports: import x from 'y', import { a, b } from 'y', import 'y'
_ES_IMPORT_RE = re.compile(
    r"^\s*import\s+(?:(?:type\s+)?(?:\*\s+as\s+(\w+)|(\w+)|"
    r"\{([^}]*)\})\s+from\s+)?['\"`]([^'\"`]+)['\"`]",
    re.MULTILINE,
)

# CommonJS: require('y') or const x = require('y')
_REQUIRE_RE = re.compile(
    r"(?:const|let|var)\s+(?:(\w+)|\{([^}]*)\})\s*=\s*require\s*\(['\"`]([^'\"`]+)['\"`]\)",
)

# class declarations
_CLASS_RE = re.compile(r"^\s*(?:export\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE)

# function declarations (named)
_FUNC_RE = re.compile(
    r"^\s*(?:export\s+)?(?:default\s+)?(?:async\s+)?function\s+(\w+)\s*\(",
    re.MULTILINE,
)

# arrow / const functions: const foo = async () => or const foo = () =>
_ARROW_RE = re.compile(
    r"^\s*(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(async\s*)?\(.*?\)\s*=>",
    re.MULTILINE,
)

# test blocks
_IT_TEST_RE = re.compile(
    r"^\s*(?:it|test)\s*\(\s*['\"`]([^'\"`]+)['\"`]",
    re.MULTILINE,
)
_DESCRIBE_RE = re.compile(
    r"^\s*describe\s*\(\s*['\"`]([^'\"`]+)['\"`]",
    re.MULTILINE,
)

# function call: identifier followed by ( — used for call graph
_CALL_RE = re.compile(r"\b([a-zA-Z_$][\w$]*)\s*\(")

# fetch/axios HTTP calls for route linking
_FETCH_RE = re.compile(
    r"fetch\s*\(\s*['\"`]([^'\"`]+)['\"`]",
)
_AXIOS_RE = re.compile(
    r"axios\s*\.\s*(get|post|put|patch|delete)\s*\(\s*['\"`]([^'\"`]+)['\"`]",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# public API
# ---------------------------------------------------------------------------

def is_test_file(path: str) -> bool:
    lower = path.lower()
    return any(lower.endswith(ext) for ext in NODE_TEST_EXTENSIONS)


def parse_imports(file_path: str, source: str) -> list[ImportInfo]:
    results: list[ImportInfo] = []

    for m in _ES_IMPORT_RE.finditer(source):
        star_alias, default_name, named_imports, module = m.groups()
        lineno = source[: m.start()].count("\n") + 1
        if star_alias:
            results.append(ImportInfo(file_path=file_path, module=module, alias=star_alias, level=0))
        elif default_name:
            results.append(ImportInfo(file_path=file_path, module=module, name=default_name, level=0))
        elif named_imports:
            for part in named_imports.split(","):
                part = part.strip()
                if not part or part == "type":
                    continue
                if " as " in part:
                    name, alias = part.split(" as ", 1)
                    results.append(ImportInfo(file_path=file_path, module=module,
                                              name=name.strip(), alias=alias.strip(), level=0))
                else:
                    results.append(ImportInfo(file_path=file_path, module=module,
                                              name=part, level=0))
        else:
            results.append(ImportInfo(file_path=file_path, module=module, level=0))

    for m in _REQUIRE_RE.finditer(source):
        name, named, module = m.groups()
        if name:
            results.append(ImportInfo(file_path=file_path, module=module, name=name, level=0))
        elif named:
            for part in named.split(","):
                part = part.strip()
                if part:
                    results.append(ImportInfo(file_path=file_path, module=module, name=part, level=0))

    return results


def parse_symbols(file_path: str, source: str) -> list[SymbolInfo]:
    results: list[SymbolInfo] = []

    for m in _CLASS_RE.finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        results.append(SymbolInfo(
            file_path=file_path, name=m.group(1),
            symbol_type="class", lineno=lineno,
        ))

    for m in _FUNC_RE.finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        is_async = "async" in m.group(0)
        results.append(SymbolInfo(
            file_path=file_path, name=m.group(1),
            symbol_type="async_function" if is_async else "function",
            lineno=lineno,
        ))

    for m in _ARROW_RE.finditer(source):
        lineno = source[: m.start()].count("\n") + 1
        is_async = bool(m.group(2))
        results.append(SymbolInfo(
            file_path=file_path, name=m.group(1),
            symbol_type="async_arrow_function" if is_async else "arrow_function",
            lineno=lineno,
        ))

    return results


def parse_routes(file_path: str, source: str) -> list[RouteInfo]:
    results: list[RouteInfo] = []
    for m in _ROUTE_RE.finditer(source):
        method, path = m.group(1).lower(), m.group(2)
        lineno = source[: m.start()].count("\n") + 1
        results.append(RouteInfo(
            file_path=file_path, method=method, path=path,
            function_name="", lineno=lineno,
        ))
    return results


def parse_tests(file_path: str, source: str) -> TestInfo:
    test_functions = [m.group(1) for m in _IT_TEST_RE.finditer(source)]
    test_classes = [m.group(1) for m in _DESCRIBE_RE.finditer(source)]
    return TestInfo(
        file_path=file_path,
        test_functions=test_functions,
        test_classes=test_classes,
    )


def parse_calls(file_path: str, source: str) -> list[CallInfo]:
    """Extract function call sites. Associates each call with its enclosing function."""
    _SKIP_KEYWORDS = {
        "if", "for", "while", "switch", "catch", "function", "class",
        "return", "typeof", "instanceof", "new", "import", "require",
        "console", "Promise", "Array", "Object", "Math", "JSON",
    }
    results: list[CallInfo] = []
    lines = source.splitlines()

    # Determine enclosing function per line (rough heuristic using named function/arrow declarations)
    func_ranges: list[tuple[int, int, str]] = []  # (start_line, end_line, name) — approx
    for m in _FUNC_RE.finditer(source):
        start = source[: m.start()].count("\n") + 1
        func_ranges.append((start, start + 50, m.group(1)))  # rough range
    for m in _ARROW_RE.finditer(source):
        start = source[: m.start()].count("\n") + 1
        func_ranges.append((start, start + 50, m.group(1)))

    def _enclosing(lineno: int) -> str:
        best: tuple[int, str] = (0, "<module>")
        for s, e, name in func_ranges:
            if s <= lineno and s > best[0]:
                best = (s, name)
        return best[1]

    for i, line in enumerate(lines, 1):
        for m in _CALL_RE.finditer(line):
            callee = m.group(1)
            if callee in _SKIP_KEYWORDS:
                continue
            results.append(CallInfo(
                caller_file=file_path,
                caller_name=_enclosing(i),
                callee_name=callee,
                lineno=i,
            ))

    return results


def parse_fetch_calls(file_path: str, source: str) -> list[RouteLink]:
    """Detect fetch() and axios.method() calls for frontend→backend route linking."""
    results: list[RouteLink] = []

    for m in _FETCH_RE.finditer(source):
        pattern = m.group(1)
        if not pattern.startswith("/"):
            continue
        lineno = source[: m.start()].count("\n") + 1
        results.append(RouteLink(
            frontend_file=file_path,
            frontend_lineno=lineno,
            pattern=pattern,
            method="unknown",
        ))

    for m in _AXIOS_RE.finditer(source):
        method, pattern = m.group(1).lower(), m.group(2)
        if not pattern.startswith("/"):
            continue
        lineno = source[: m.start()].count("\n") + 1
        results.append(RouteLink(
            frontend_file=file_path,
            frontend_lineno=lineno,
            pattern=pattern,
            method=method,
        ))

    return results
