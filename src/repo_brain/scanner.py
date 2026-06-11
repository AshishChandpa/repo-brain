from __future__ import annotations

from collections import Counter
from pathlib import Path

from repo_brain.config import Config
from repo_brain.models import FileInfo, ScanResult
from repo_brain.parsers import go, node
from repo_brain.parsers.fastapi import parse_routes as parse_fastapi_routes
from repo_brain.parsers.pytest import is_test_file as is_py_test, parse_tests as parse_py_tests
from repo_brain.parsers.python_ast import parse_imports as parse_py_imports
from repo_brain.parsers.python_ast import parse_symbols as parse_py_symbols

_NODE_EXTENSIONS = {".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx"}
_GO_EXTENSIONS = {".go"}
_PY_EXTENSIONS = {".py"}


def scan(root: Path, config: Config) -> ScanResult:
    exclude = set(config.exclude_dirs)
    extensions = set(config.include_extensions)

    all_files = _collect_files(root, config.source_roots, exclude, extensions)

    files: list[FileInfo] = []
    all_imports = []
    all_symbols = []
    all_routes = []
    all_tests = []

    for abs_path, rel_path in all_files:
        source = abs_path.read_text(encoding="utf-8", errors="replace")
        lines = source.count("\n") + 1
        ext = Path(rel_path).suffix.lower()

        is_test, module_path = False, None

        if ext in _PY_EXTENSIONS:
            is_test = is_py_test(rel_path)
            module_path = _to_module_path(rel_path, ext)
            all_imports.extend(parse_py_imports(rel_path, source))
            all_symbols.extend(parse_py_symbols(rel_path, source))
            all_routes.extend(parse_fastapi_routes(rel_path, source))
            if is_test:
                all_tests.append(parse_py_tests(rel_path, source))

        elif ext in _NODE_EXTENSIONS:
            is_test = node.is_test_file(rel_path)
            module_path = _to_module_path(rel_path, ext)
            all_imports.extend(node.parse_imports(rel_path, source))
            all_symbols.extend(node.parse_symbols(rel_path, source))
            all_routes.extend(node.parse_routes(rel_path, source))
            if is_test:
                all_tests.append(node.parse_tests(rel_path, source))

        elif ext in _GO_EXTENSIONS:
            is_test = go.is_test_file(rel_path)
            module_path = _to_module_path(rel_path, ext)
            all_imports.extend(go.parse_imports(rel_path, source))
            all_symbols.extend(go.parse_symbols(rel_path, source))
            all_routes.extend(go.parse_routes(rel_path, source))
            if is_test:
                all_tests.append(go.parse_tests(rel_path, source))

        files.append(FileInfo(
            path=rel_path,
            module_path=module_path,
            line_count=lines,
            is_test=is_test,
        ))

    return ScanResult(
        files=files,
        imports=all_imports,
        symbols=all_symbols,
        routes=all_routes,
        tests=all_tests,
    )


def file_counts_by_language(files: list[FileInfo]) -> dict[str, int]:
    counts: Counter = Counter()
    for f in files:
        ext = Path(f.path).suffix.lower()
        if ext in _PY_EXTENSIONS:
            counts["python"] += 1
        elif ext in _NODE_EXTENSIONS:
            counts["node"] += 1
        elif ext in _GO_EXTENSIONS:
            counts["go"] += 1
        else:
            counts["other"] += 1
    return dict(counts)


def top_level_modules(files: list[FileInfo], root: Path) -> list[str]:
    modules: set[str] = set()
    for f in files:
        parts = Path(f.path).parts
        if len(parts) > 1:
            modules.add(parts[0])
        elif parts:
            stem = Path(parts[0]).stem
            if stem not in ("__init__", "go"):
                modules.add(stem)
    return sorted(modules)


def _collect_files(
    root: Path,
    source_roots: list[str],
    exclude: set[str],
    extensions: set[str],
) -> list[tuple[Path, str]]:
    results: list[tuple[Path, str]] = []
    for source_root in source_roots:
        base = (root / source_root).resolve()
        if not base.exists():
            continue
        for path in sorted(base.rglob("*")):
            if path.suffix.lower() not in extensions:
                continue
            if _is_excluded(path, base, exclude):
                continue
            rel = str(path.relative_to(base))
            results.append((path, rel))
    return results


def _is_excluded(path: Path, base: Path, exclude: set[str]) -> bool:
    try:
        rel = path.relative_to(base)
    except ValueError:
        return False
    for part in rel.parts:
        if part in exclude:
            return True
    return False


def _to_module_path(rel_path: str, ext: str) -> str | None:
    p = Path(rel_path)
    parts = list(p.with_suffix("").parts)
    if ext in _PY_EXTENSIONS and parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)