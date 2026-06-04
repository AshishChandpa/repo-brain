from __future__ import annotations

from pathlib import Path

from repo_brain.config import Config
from repo_brain.models import FileInfo, ScanResult
from repo_brain.parsers.fastapi import parse_routes
from repo_brain.parsers.pytest import is_test_file, parse_tests
from repo_brain.parsers.python_ast import parse_imports, parse_symbols


def scan(root: Path, config: Config) -> ScanResult:
    exclude = set(config.exclude_dirs)
    extensions = set(config.include_extensions)

    py_files = _collect_files(root, config.source_roots, exclude, extensions)

    files: list[FileInfo] = []
    all_imports = []
    all_symbols = []
    all_routes = []
    all_tests = []

    for abs_path, rel_path in py_files:
        source = abs_path.read_text(encoding="utf-8", errors="replace")
        lines = source.count("\n") + 1
        test = is_test_file(rel_path)
        module_path = _to_module_path(rel_path)

        files.append(FileInfo(
            path=rel_path,
            module_path=module_path,
            line_count=lines,
            is_test=test,
        ))

        all_imports.extend(parse_imports(rel_path, source))
        all_symbols.extend(parse_symbols(rel_path, source))
        all_routes.extend(parse_routes(rel_path, source))

        if test:
            all_tests.append(parse_tests(rel_path, source))

    return ScanResult(
        files=files,
        imports=all_imports,
        symbols=all_symbols,
        routes=all_routes,
        tests=all_tests,
    )


def top_level_modules(files: list[FileInfo], root: Path) -> list[str]:
    modules: set[str] = set()
    for f in files:
        parts = Path(f.path).parts
        if len(parts) > 1:
            modules.add(parts[0])
        elif parts:
            stem = Path(parts[0]).stem
            if stem != "__init__":
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
            if path.suffix not in extensions:
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


def _to_module_path(rel_path: str) -> str | None:
    p = Path(rel_path)
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return None
    return ".".join(parts)
