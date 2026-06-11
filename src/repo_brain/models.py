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
    symbol_type: Literal[
        "class", "function", "async_function", "method", "async_method",
        "struct", "interface", "arrow_function", "async_arrow_function",
    ]
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
    file_counts: dict[str, int] = {}
    top_level_modules: list[str]
    artifact_paths: dict[str, str]


class ScanResult(BaseModel):
    files: list[FileInfo]
    imports: list[ImportInfo]
    symbols: list[SymbolInfo]
    routes: list[RouteInfo]
    tests: list[TestInfo]


class ImpactResult(BaseModel):
    target_file: str
    module_path: str | None
    symbols: list[SymbolInfo]
    routes: list[RouteInfo]
    imported_by: list[str]
    related_tests: list[str]
    likely_affected: list[str]


class ScoredFile(BaseModel):
    path: str
    score: int


class ScoredSymbol(BaseModel):
    symbol: SymbolInfo
    score: int


class ContextResult(BaseModel):
    task: str
    keywords: list[str]
    suggested_files: list[ScoredFile]
    suggested_symbols: list[ScoredSymbol]
    suggested_routes: list[RouteInfo]
    suggested_tests: list[str]
