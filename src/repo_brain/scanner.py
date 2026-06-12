from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

from repo_brain.config import Config
from repo_brain.models import CallInfo, FileInfo, RouteInfo, RouteLink, ScanResult
from repo_brain.parsers import go, node
from repo_brain.parsers.fastapi import parse_routes as parse_fastapi_routes
from repo_brain.parsers.pytest import is_test_file as is_py_test, parse_tests as parse_py_tests
from repo_brain.parsers.python_ast import parse_calls as parse_py_calls
from repo_brain.parsers.python_ast import parse_imports as parse_py_imports
from repo_brain.parsers.python_ast import parse_symbols as parse_py_symbols

_NODE_EXTENSIONS = {".js", ".ts", ".mjs", ".cjs", ".jsx", ".tsx"}
_GO_EXTENSIONS = {".go"}
_PY_EXTENSIONS = {".py"}


def scan(root: Path, config: Config) -> ScanResult:
    """Full scan — parse every file regardless of cache."""
    exclude = set(config.exclude_dirs)
    extensions = set(config.include_extensions)
    all_files = _collect_files(root, config.source_roots, exclude, extensions)
    return _parse_files(all_files)


def scan_incremental(
    root: Path,
    config: Config,
    brain_dir: Path,
) -> tuple[ScanResult, dict[str, str]]:
    """Incremental scan — skip files whose SHA-256 hash hasn't changed.

    Returns (ScanResult, new_hashes_dict). The caller should persist new_hashes
    to brain_dir/file_hashes.json after writing artifacts.
    """
    exclude = set(config.exclude_dirs)
    extensions = set(config.include_extensions)
    all_files = _collect_files(root, config.source_roots, exclude, extensions)

    old_hashes = _load_hashes(brain_dir)
    old_artifacts = _load_cached_artifacts(brain_dir)

    new_hashes: dict[str, str] = {}
    changed_paths: set[str] = set()

    for abs_path, rel_path in all_files:
        digest = _sha256(abs_path)
        new_hashes[rel_path] = digest
        if old_hashes.get(rel_path) != digest:
            changed_paths.add(rel_path)

    deleted_paths = set(old_hashes.keys()) - {rel for _, rel in all_files}

    if not changed_paths and not deleted_paths:
        return _reconstruct_from_cache(old_artifacts, all_files), new_hashes

    changed_result = _parse_files(
        [(abs_p, rel_p) for abs_p, rel_p in all_files if rel_p in changed_paths]
    )

    skip = changed_paths | deleted_paths
    merged_result = ScanResult(
        files=[f for f in old_artifacts.get("files", []) if f.path not in skip] + changed_result.files,
        imports=[i for i in old_artifacts.get("imports", []) if i.file_path not in skip] + changed_result.imports,
        symbols=[s for s in old_artifacts.get("symbols", []) if s.file_path not in skip] + changed_result.symbols,
        routes=[r for r in old_artifacts.get("routes", []) if r.file_path not in skip] + changed_result.routes,
        tests=[t for t in old_artifacts.get("tests", []) if t.file_path not in skip] + changed_result.tests,
        calls=[c for c in old_artifacts.get("calls", []) if c.caller_file not in skip] + changed_result.calls,
        route_links=[],
    )
    merged_result.route_links = _link_routes(merged_result.route_links, merged_result.routes)
    return merged_result, new_hashes


# ---------------------------------------------------------------------------
# core parsing
# ---------------------------------------------------------------------------

def _parse_files(file_list: list[tuple[Path, str]]) -> ScanResult:
    files: list[FileInfo] = []
    all_imports = []
    all_symbols = []
    all_routes = []
    all_tests = []
    all_calls: list[CallInfo] = []
    all_route_links: list[RouteLink] = []

    for abs_path, rel_path in file_list:
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
            all_calls.extend(parse_py_calls(rel_path, source))
            if is_test:
                all_tests.append(parse_py_tests(rel_path, source))

        elif ext in _NODE_EXTENSIONS:
            is_test = node.is_test_file(rel_path)
            module_path = _to_module_path(rel_path, ext)
            all_imports.extend(node.parse_imports(rel_path, source))
            all_symbols.extend(node.parse_symbols(rel_path, source))
            all_routes.extend(node.parse_routes(rel_path, source))
            all_calls.extend(node.parse_calls(rel_path, source))
            all_route_links.extend(node.parse_fetch_calls(rel_path, source))
            if is_test:
                all_tests.append(node.parse_tests(rel_path, source))

        elif ext in _GO_EXTENSIONS:
            is_test = go.is_test_file(rel_path)
            module_path = _to_module_path(rel_path, ext)
            all_imports.extend(go.parse_imports(rel_path, source))
            all_symbols.extend(go.parse_symbols(rel_path, source))
            all_routes.extend(go.parse_routes(rel_path, source))
            all_calls.extend(go.parse_calls(rel_path, source))
            if is_test:
                all_tests.append(go.parse_tests(rel_path, source))

        files.append(FileInfo(
            path=rel_path,
            module_path=module_path,
            line_count=lines,
            is_test=is_test,
        ))

    result = ScanResult(
        files=files,
        imports=all_imports,
        symbols=all_symbols,
        routes=all_routes,
        tests=all_tests,
        calls=all_calls,
        route_links=all_route_links,
    )
    result.route_links = _link_routes(result.route_links, result.routes)
    return result


# ---------------------------------------------------------------------------
# route linking
# ---------------------------------------------------------------------------

def _link_routes(links: list[RouteLink], backend_routes: list[RouteInfo]) -> list[RouteLink]:
    linked: list[RouteLink] = []
    for link in links:
        match = _find_matching_route(link.pattern, link.method, backend_routes)
        linked.append(RouteLink(
            frontend_file=link.frontend_file,
            frontend_lineno=link.frontend_lineno,
            pattern=link.pattern,
            method=link.method,
            backend_route=match,
        ))
    return linked


def _find_matching_route(pattern: str, method: str, routes: list[RouteInfo]) -> RouteInfo | None:
    for r in routes:
        if r.path == pattern and (method == "unknown" or r.method == method):
            return r
    for r in routes:
        if (r.path in pattern or pattern in r.path) and (method == "unknown" or r.method == method):
            return r
    return None


# ---------------------------------------------------------------------------
# hashing + caching
# ---------------------------------------------------------------------------

def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def _load_hashes(brain_dir: Path) -> dict[str, str]:
    p = brain_dir / "file_hashes.json"
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text())
    except Exception:
        return {}


def _load_cached_artifacts(brain_dir: Path) -> dict:
    from repo_brain.models import CallInfo, FileInfo, ImportInfo, RouteInfo, SymbolInfo, TestInfo

    def _read(name: str) -> list:
        p = brain_dir / name
        try:
            return json.loads(p.read_text()) if p.exists() else []
        except Exception:
            return []

    return {
        "files": [],  # files reconstructed from filesystem in _reconstruct_from_cache
        "imports": [ImportInfo(**i) for i in _read("imports.json")],
        "symbols": [SymbolInfo(**s) for s in _read("symbols.json")],
        "routes": [RouteInfo(**r) for r in _read("routes.json")],
        "tests": [TestInfo(**t) for t in _read("tests.json")],
        "calls": [CallInfo(**c) for c in _read("call_graph.json")],
    }


def _reconstruct_from_cache(old_artifacts: dict, all_files: list[tuple[Path, str]]) -> ScanResult:
    files = []
    for abs_path, rel_path in all_files:
        source = abs_path.read_text(encoding="utf-8", errors="replace")
        lines = source.count("\n") + 1
        ext = Path(rel_path).suffix.lower()
        is_test = False
        if ext in _PY_EXTENSIONS:
            is_test = is_py_test(rel_path)
        elif ext in _NODE_EXTENSIONS:
            is_test = node.is_test_file(rel_path)
        elif ext in _GO_EXTENSIONS:
            is_test = go.is_test_file(rel_path)
        files.append(FileInfo(
            path=rel_path,
            module_path=_to_module_path(rel_path, ext),
            line_count=lines,
            is_test=is_test,
        ))

    return ScanResult(
        files=files,
        imports=old_artifacts.get("imports", []),
        symbols=old_artifacts.get("symbols", []),
        routes=old_artifacts.get("routes", []),
        tests=old_artifacts.get("tests", []),
        calls=old_artifacts.get("calls", []),
        route_links=[],
    )


# ---------------------------------------------------------------------------
# utilities
# ---------------------------------------------------------------------------

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
