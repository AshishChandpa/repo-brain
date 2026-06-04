from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class FileInfo(BaseModel):
    path: str
    module_path: str | None = None
    line_count: int
    is_test: bool = False


class ImportInfo(BaseModel):
    file_path: str
    module: str
    name: str | None = None
    alias: str | None = None
    level: int = 0


class SymbolInfo(BaseModel):
    file_path: str
    name: str
    symbol_type: Literal["class", "function", "async_function", "method", "async_method"]
    lineno: int
    end_lineno: int | None = None
    parent: str | None = None


class RouteInfo(BaseModel):
    file_path: str
    method: str
    path: str
    function_name: str
    lineno: int


class TestInfo(BaseModel):
    file_path: str
    test_functions: list[str]
    test_classes: list[str]


class RepoMap(BaseModel):
    project_name: str | None
    scan_timestamp: str
    python_file_count: int
    top_level_modules: list[str]
    artifact_paths: dict[str, str]


class ScanResult(BaseModel):
    files: list[FileInfo]
    imports: list[ImportInfo]
    symbols: list[SymbolInfo]
    routes: list[RouteInfo]
    tests: list[TestInfo]
