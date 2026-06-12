from __future__ import annotations

import ast
from pathlib import Path

from repo_brain.models import CallInfo, ImportInfo, SymbolInfo

SUPPORTED_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def parse_imports(file_path: str, source: str) -> list[ImportInfo]:
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    results: list[ImportInfo] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                results.append(ImportInfo(
                    file_path=file_path,
                    module=alias.name,
                    name=None,
                    alias=alias.asname,
                    level=0,
                ))
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                results.append(ImportInfo(
                    file_path=file_path,
                    module=module,
                    name=alias.name,
                    alias=alias.asname,
                    level=node.level,
                ))
    return results


def parse_symbols(file_path: str, source: str) -> list[SymbolInfo]:
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    results: list[SymbolInfo] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            results.append(SymbolInfo(
                file_path=file_path,
                name=node.name,
                symbol_type="class",
                lineno=node.lineno,
                end_lineno=node.end_lineno,
                parent=None,
            ))
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    stype = "async_method" if isinstance(child, ast.AsyncFunctionDef) else "method"
                    results.append(SymbolInfo(
                        file_path=file_path,
                        name=child.name,
                        symbol_type=stype,
                        lineno=child.lineno,
                        end_lineno=child.end_lineno,
                        parent=node.name,
                    ))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # skip if this is a method (already captured above)
            if _is_top_level_function(tree, node):
                stype = "async_function" if isinstance(node, ast.AsyncFunctionDef) else "function"
                results.append(SymbolInfo(
                    file_path=file_path,
                    name=node.name,
                    symbol_type=stype,
                    lineno=node.lineno,
                    end_lineno=node.end_lineno,
                    parent=None,
                ))

    return results


def parse_calls(file_path: str, source: str) -> list[CallInfo]:
    """Extract function call relationships using AST.

    Returns one CallInfo per call site: which enclosing function made the call
    and what callee name was invoked.
    """
    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return []

    # Build a map: ast node id → enclosing function name
    _parent: dict[int, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            _parent[id(child)] = node

    results: list[CallInfo] = []

    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue

        # Extract callee name (best-effort)
        callee = _callee_name(node.func)
        if not callee:
            continue

        # Find enclosing function
        enclosing = _enclosing_function(_parent, node)
        results.append(CallInfo(
            caller_file=file_path,
            caller_name=enclosing,
            callee_name=callee,
            lineno=node.lineno,
        ))

    return results


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _callee_name(func_node: ast.expr) -> str:
    """Return a string name for the call target, or empty string if not representable."""
    if isinstance(func_node, ast.Name):
        return func_node.id
    if isinstance(func_node, ast.Attribute):
        return func_node.attr
    return ""


def _enclosing_function(parent_map: dict[int, ast.AST], node: ast.AST) -> str:
    """Walk up the parent map to find the nearest enclosing function name."""
    current = parent_map.get(id(node))
    while current is not None:
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return current.name
        current = parent_map.get(id(current))
    return "<module>"


def _is_top_level_function(tree: ast.Module, target: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in ast.walk(node):
                if child is target:
                    return False
    return True
