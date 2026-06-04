from __future__ import annotations

import json
from pathlib import Path

from repo_brain.models import ImpactResult, ImportInfo, RouteInfo, SymbolInfo, TestInfo


def load_impact_artifacts(brain_dir: Path) -> tuple[
    list[SymbolInfo],
    list[RouteInfo],
    list[ImportInfo],
    list[TestInfo],
]:
    def _read(name: str) -> list:
        p = brain_dir / name
        return json.loads(p.read_text()) if p.exists() else []

    symbols = [SymbolInfo(**s) for s in _read("symbols.json")]
    routes = [RouteInfo(**r) for r in _read("routes.json")]
    imports = [ImportInfo(**i) for i in _read("imports.json")]
    tests = [TestInfo(**t) for t in _read("tests.json")]
    return symbols, routes, imports, tests


def analyse(
    target: str,
    symbols: list[SymbolInfo],
    routes: list[RouteInfo],
    imports: list[ImportInfo],
    tests: list[TestInfo],
) -> ImpactResult:
    target_path = Path(target)
    module_path = _to_module_path(target)
    module_variants = _module_variants(target_path)

    # symbols and routes defined inside the target file
    file_symbols = [s for s in symbols if _paths_match(s.file_path, target)]
    file_routes = [r for r in routes if _paths_match(r.file_path, target)]

    # files that import this module (reverse lookup)
    imported_by: list[str] = _find_importers(imports, module_variants, target)

    # test files: any importer that is a test file, plus name-heuristic matches
    test_file_paths = {t.file_path for t in tests}
    related_tests: list[str] = sorted({
        *[f for f in imported_by if f in test_file_paths],
        *_name_heuristic_tests(target_path, test_file_paths),
    })

    # likely affected = importers + related tests, deduped, excluding the target itself
    likely_affected: list[str] = sorted({
        f for f in (*imported_by, *related_tests)
        if not _paths_match(f, target)
    })

    return ImpactResult(
        target_file=target,
        module_path=module_path,
        symbols=file_symbols,
        routes=file_routes,
        imported_by=imported_by,
        related_tests=related_tests,
        likely_affected=likely_affected,
    )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _paths_match(a: str, b: str) -> bool:
    return Path(a).resolve() == Path(b).resolve() or a == b


def _to_module_path(file_path: str) -> str | None:
    p = Path(file_path)
    if p.suffix != ".py":
        return None
    parts = list(p.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else None


def _module_variants(path: Path) -> list[str]:
    """Return several possible module names for a given file path.

    Given src/services/doc.py returns:
      ["src.services.doc", "services.doc", "doc"]
    Also handles __init__.py → package name.
    """
    parts = list(path.with_suffix("").parts)
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    if not parts:
        return []
    variants: list[str] = []
    for start in range(len(parts)):
        variants.append(".".join(parts[start:]))
    return variants


def _find_importers(
    imports: list[ImportInfo],
    module_variants: list[str],
    target: str,
) -> list[str]:
    """Files that import any module variant of the target.

    Handles both:
      import app.services.doc          → module="app.services.doc"
      from app import document_service → module="app", name="document_service"
                                         combined = "app.document_service"
    """
    variants = set(module_variants)
    found: set[str] = set()
    for imp in imports:
        if _paths_match(imp.file_path, target):
            continue
        # direct module match
        if imp.module in variants:
            found.add(imp.file_path)
            continue
        # from <pkg> import <submodule> — combine to check "pkg.submodule"
        if imp.name:
            combined = f"{imp.module}.{imp.name}" if imp.module else imp.name
            if combined in variants:
                found.add(imp.file_path)
    return sorted(found)


def _name_heuristic_tests(target_path: Path, test_file_paths: set[str]) -> list[str]:
    """Match test_<stem>.py or <stem>_test.py against known test files."""
    stem = target_path.stem
    candidates = {f"test_{stem}.py", f"{stem}_test.py"}
    return [
        f for f in test_file_paths
        if Path(f).name in candidates
    ]