from __future__ import annotations

import ast
from pathlib import Path

from repo_brain.models import ImportInfo, SymbolInfo

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


def _is_top_level_function(tree: ast.Module, target: ast.FunctionDef | ast.AsyncFunctionDef) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in ast.walk(node):
                if child is target:
                    return False
    return True
