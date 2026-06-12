from __future__ import annotations

import json
from pathlib import Path

from repo_brain.models import SymbolGap, SymbolInfo, TestInfo

# Symbol types that should have test coverage
_TESTABLE_TYPES = {"class", "function", "async_function"}


def load_gaps_artifacts(brain_dir: Path) -> tuple[list[SymbolInfo], list[TestInfo]]:
    def _read(name: str) -> list:
        p = brain_dir / name
        return json.loads(p.read_text()) if p.exists() else []

    symbols = [SymbolInfo(**s) for s in _read("symbols.json")]
    tests = [TestInfo(**t) for t in _read("tests.json")]
    return symbols, tests


def find_gaps(
    symbols: list[SymbolInfo],
    tests: list[TestInfo],
    file_filter: str | None = None,
) -> list[SymbolGap]:
    """Return symbols that have no apparent test coverage.

    A symbol is considered covered if its name (case-insensitive) appears in
    any test function name or test class name, or if the source file name
    matches a test file by stem (test_<stem>.py / <stem>_test.py).
    """
    # Build lookup sets from test data
    test_function_names: set[str] = set()
    test_class_names: set[str] = set()
    tested_stems: set[str] = set()

    for t in tests:
        for fn in t.test_functions:
            test_function_names.add(fn.lower())
        for cls in t.test_classes:
            test_class_names.add(cls.lower())
        stem = Path(t.file_path).stem.lower()
        # strip test_ prefix or _test suffix to get the subject stem
        if stem.startswith("test_"):
            tested_stems.add(stem[5:])
        elif stem.endswith("_test"):
            tested_stems.add(stem[:-5])
        else:
            tested_stems.add(stem)

    gaps: list[SymbolGap] = []

    for sym in symbols:
        if sym.symbol_type not in _TESTABLE_TYPES:
            continue
        if file_filter and not _paths_match(sym.file_path, file_filter):
            continue

        # Skip test files themselves
        stem = Path(sym.file_path).stem.lower()
        if stem.startswith("test_") or stem.endswith("_test") or stem.endswith(".test") or stem.endswith(".spec"):
            continue

        name_lower = sym.name.lower()
        file_stem = stem

        # Covered if: symbol name appears in a test function/class name
        if _name_in_tests(name_lower, test_function_names, test_class_names):
            continue

        # Covered if: file stem matches a test file stem
        if file_stem in tested_stems:
            continue

        gaps.append(SymbolGap(
            file_path=sym.file_path,
            symbol_name=sym.name,
            symbol_type=sym.symbol_type,
            lineno=sym.lineno,
        ))

    return sorted(gaps, key=lambda g: (g.file_path, g.lineno))


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _name_in_tests(name: str, fn_names: set[str], cls_names: set[str]) -> bool:
    """True if the symbol name (or a camelCase part of it) is referenced in test names."""
    for test_name in fn_names | cls_names:
        if name in test_name or test_name in name:
            return True
    return False


def _paths_match(a: str, b: str) -> bool:
    return Path(a).resolve() == Path(b).resolve() or a == b or Path(a).name == Path(b).name
