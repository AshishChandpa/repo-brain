from __future__ import annotations

import ast

from repo_brain.models import RouteInfo

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def parse_routes(file_path: str, source: str) -> list[RouteInfo]:
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    results: list[RouteInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            route = _extract_route(file_path, decorator, node.name)
            if route:
                results.append(route)

    return results


def _extract_route(
    file_path: str,
    decorator: ast.expr,
    function_name: str,
) -> RouteInfo | None:
    if not isinstance(decorator, ast.Call):
        return None

    func = decorator.func
    if not isinstance(func, ast.Attribute):
        return None

    method = func.attr.lower()
    if method not in SUPPORTED_METHODS:
        return None

    # first positional arg must be a plain string literal
    if not decorator.args:
        return None
    first_arg = decorator.args[0]
    if not isinstance(first_arg, ast.Constant) or not isinstance(first_arg.value, str):
        return None

    return RouteInfo(
        file_path=file_path,
        method=method,
        path=first_arg.value,
        function_name=function_name,
        lineno=decorator.lineno,
    )
