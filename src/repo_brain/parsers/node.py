from __future__ import annotations

import re

from repo_brain.models import ImportInfo, RouteInfo, SymbolInfo, TestInfo

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