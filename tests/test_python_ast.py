from repo_brain.parsers.python_ast import parse_imports, parse_symbols

SAMPLE = """
import os
import sys as system
from pathlib import Path
from . import utils
from ..models import User

class MyClass:
    def method_one(self):
        pass

    async def async_method(self):
        pass

def top_func():
    pass

async def async_top():
    pass
"""


def test_imports_absolute():
    imports = parse_imports("sample.py", SAMPLE)
    modules = [(i.module, i.name, i.alias, i.level) for i in imports]
    assert ("os", None, None, 0) in modules
    assert ("sys", None, "system", 0) in modules
    assert ("pathlib", "Path", None, 0) in modules


def test_imports_relative():
    imports = parse_imports("sample.py", SAMPLE)
    relative = [i for i in imports if i.level > 0]
    assert any(i.level == 1 and i.name == "utils" for i in relative)
    assert any(i.level == 2 and i.module == "models" and i.name == "User" for i in relative)


def test_symbols_class():
    symbols = parse_symbols("sample.py", SAMPLE)
    classes = [s for s in symbols if s.symbol_type == "class"]
    assert any(s.name == "MyClass" for s in classes)


def test_symbols_methods():
    symbols = parse_symbols("sample.py", SAMPLE)
    methods = [s for s in symbols if s.symbol_type == "method"]
    assert any(s.name == "method_one" and s.parent == "MyClass" for s in methods)


def test_symbols_async_method():
    symbols = parse_symbols("sample.py", SAMPLE)
    async_methods = [s for s in symbols if s.symbol_type == "async_method"]
    assert any(s.name == "async_method" and s.parent == "MyClass" for s in async_methods)


def test_symbols_top_level_function():
    symbols = parse_symbols("sample.py", SAMPLE)
    funcs = [s for s in symbols if s.symbol_type == "function"]
    assert any(s.name == "top_func" and s.parent is None for s in funcs)


def test_symbols_async_top_level():
    symbols = parse_symbols("sample.py", SAMPLE)
    async_funcs = [s for s in symbols if s.symbol_type == "async_function"]
    assert any(s.name == "async_top" and s.parent is None for s in async_funcs)


def test_syntax_error_returns_empty():
    assert parse_imports("bad.py", "def (broken:") == []
    assert parse_symbols("bad.py", "def (broken:") == []
