from __future__ import annotations

import json
import re
from pathlib import Path

from repo_brain.models import (
    ContextResult,
    ImportInfo,
    RouteInfo,
    ScoredFile,
    ScoredSymbol,
    SymbolInfo,
    TestInfo,
)

# Words that carry no signal for file/symbol matching
_STOPWORDS = {
    "a", "an", "the", "and", "or", "in", "on", "at", "to", "for",
    "of", "with", "from", "by", "as", "is", "it", "be", "do",
    "add", "fix", "get", "set", "make", "use", "run", "put", "new",
    "update", "change", "edit", "create", "remove", "delete", "handle",
    "implement", "this", "that", "into",
}

_TOP_N_FILES = 10
_TOP_N_SYMBOLS = 10


def load_context_artifacts(brain_dir: Path) -> tuple[
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


def build_context(
    task: str,
    symbols: list[SymbolInfo],
    routes: list[RouteInfo],
    imports: list[ImportInfo],
    tests: list[TestInfo],
) -> ContextResult:
    keywords = _extract_keywords(task)

    # collect unique file paths from all artifacts
    all_files: set[str] = set()
    for s in symbols:
        all_files.add(s.file_path)
    for r in routes:
        all_files.add(r.file_path)
    for i in imports:
        all_files.add(i.file_path)
    for t in tests:
        all_files.add(t.file_path)

    # score files
    scored_files = _score_files(sorted(all_files), keywords)

    # score symbols
    scored_symbols = _score_symbols(symbols, keywords)

    # match routes
    matched_routes = _match_routes(routes, keywords)

    # match test files
    test_file_paths = [t.file_path for t in tests]
    matched_tests = _match_tests(tests, keywords)

    return ContextResult(
        task=task,
        keywords=keywords,
        suggested_files=scored_files[:_TOP_N_FILES],
        suggested_symbols=scored_symbols[:_TOP_N_SYMBOLS],
        suggested_routes=matched_routes,
        suggested_tests=matched_tests,
    )


# ---------------------------------------------------------------------------
# tokenizer
# ---------------------------------------------------------------------------

def _extract_keywords(task: str) -> list[str]:
    # split camelCase: "documentUpload" → ["document", "Upload"]
    task = re.sub(r"([a-z])([A-Z])", r"\1 \2", task)
    # split on non-alphanumeric
    tokens = re.split(r"[^a-zA-Z0-9]+", task)
    seen: set[str] = set()
    result: list[str] = []
    for t in tokens:
        word = t.lower()
        if word and word not in _STOPWORDS and word not in seen:
            seen.add(word)
            result.append(word)
    return result


# ---------------------------------------------------------------------------
# scorers
# ---------------------------------------------------------------------------

def _tokenize_path(path: str) -> list[str]:
    """Split a file path into lowercase tokens for matching."""
    # strip extension
    stem = Path(path).with_suffix("").as_posix()
    # split on / _ - and camelCase
    stem = re.sub(r"([a-z])([A-Z])", r"\1 \2", stem)
    return [t.lower() for t in re.split(r"[^a-zA-Z0-9]+", stem) if t]


def _score_token_list(tokens: list[str], keywords: list[str]) -> int:
    token_set = set(tokens)
    return sum(1 for kw in keywords if kw in token_set)


def _score_files(file_paths: list[str], keywords: list[str]) -> list[ScoredFile]:
    scored: list[ScoredFile] = []
    for path in file_paths:
        tokens = _tokenize_path(path)
        score = _score_token_list(tokens, keywords)
        if score > 0:
            scored.append(ScoredFile(path=path, score=score))
    return sorted(scored, key=lambda x: x.score, reverse=True)


def _score_symbols(symbols: list[SymbolInfo], keywords: list[str]) -> list[ScoredSymbol]:
    scored: list[ScoredSymbol] = []
    for sym in symbols:
        name_tokens = _tokenize_path(sym.name)
        path_tokens = _tokenize_path(sym.file_path)
        parent_tokens = _tokenize_path(sym.parent) if sym.parent else []
        all_tokens = name_tokens + path_tokens + parent_tokens
        score = _score_token_list(all_tokens, keywords)
        if score > 0:
            scored.append(ScoredSymbol(symbol=sym, score=score))
    return sorted(scored, key=lambda x: x.score, reverse=True)


def _match_routes(routes: list[RouteInfo], keywords: list[str]) -> list[RouteInfo]:
    matched: list[RouteInfo] = []
    for route in routes:
        tokens = (
            _tokenize_path(route.path)
            + _tokenize_path(route.function_name)
            + _tokenize_path(route.file_path)
        )
        if _score_token_list(tokens, keywords) > 0:
            matched.append(route)
    return matched


def _match_tests(tests: list[TestInfo], keywords: list[str]) -> list[str]:
    matched: list[str] = []
    for t in tests:
        tokens = _tokenize_path(t.file_path)
        for fn in t.test_functions:
            tokens += _tokenize_path(fn)
        for cls in t.test_classes:
            tokens += _tokenize_path(cls)
        if _score_token_list(tokens, keywords) > 0:
            matched.append(t.file_path)
    return sorted(set(matched))