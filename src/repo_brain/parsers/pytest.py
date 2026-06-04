from __future__ import annotations

import ast
from pathlib import Path

from repo_brain.models import TestInfo

TEST_FILE_PATTERNS = ("test_", "_test")


def is_test_file(path: str) -> bool:
    stem = Path(path).stem
    return stem.startswith("test_") or stem.endswith("_test")


def parse_tests(file_path: str, source: str) -> TestInfo:
    test_functions: list[str] = []
    test_classes: list[str] = []

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError:
        return TestInfo(file_path=file_path, test_functions=[], test_classes=[])

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith("test_"):
                test_functions.append(node.name)
        elif isinstance(node, ast.ClassDef):
            if node.name.startswith("Test"):
                test_classes.append(node.name)
                for child in node.body:
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if child.name.startswith("test_"):
                            test_functions.append(f"{node.name}.{child.name}")

    return TestInfo(
        file_path=file_path,
        test_functions=test_functions,
        test_classes=test_classes,
    )
