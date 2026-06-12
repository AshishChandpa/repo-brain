from __future__ import annotations

import json
from pathlib import Path

from repo_brain.context import build_context, load_context_artifacts

_TOP_N_FILES = 5
_TOP_N_SYMBOLS = 8
_MAX_SNIPPET_LINES = 60


def export_context(
    task: str,
    brain_dir: Path,
    root: Path,
) -> str:
    """Return a Markdown document with actual code snippets for the given task.

    Runs context analysis, then for each top suggested symbol extracts the
    source lines (lineno → end_lineno) and formats them as fenced code blocks.
    Falls back to file-level excerpts when symbols span no line range.
    """
    symbols, routes, imports, tests = load_context_artifacts(brain_dir)
    result = build_context(task, symbols, routes, imports, tests)

    sections: list[str] = []
    sections.append(f"# Context export: {task}\n")
    sections.append(f"**Keywords:** {', '.join(result.keywords) or '(none)'}\n")

    if result.suggested_routes:
        sections.append("\n## Routes involved\n")
        for r in result.suggested_routes[:5]:
            sections.append(f"- `{r.method.upper()} {r.path}` → `{r.function_name}` ({r.file_path}:{r.lineno})")

    if result.suggested_tests:
        sections.append("\n## Tests to run\n")
        for t in result.suggested_tests[:5]:
            sections.append(f"- `{t}`")

    # Emit code snippets for top symbols, grouped by file
    emitted_files: set[str] = set()
    symbol_snippets: list[str] = []

    for ss in result.suggested_symbols[:_TOP_N_SYMBOLS]:
        sym = ss.symbol
        file_path = root / sym.file_path
        if not file_path.exists():
            continue
        snippet = _extract_snippet(file_path, sym.lineno, sym.end_lineno)
        if not snippet:
            continue
        lang = _lang(sym.file_path)
        label = f"`{sym.name}` ({sym.symbol_type}) — {sym.file_path}:{sym.lineno}"
        symbol_snippets.append(f"\n### {label}\n\n```{lang}\n{snippet}\n```")
        emitted_files.add(sym.file_path)

    if symbol_snippets:
        sections.append("\n## Key symbols\n")
        sections.extend(symbol_snippets)

    # For top suggested files not already covered by symbol snippets
    file_snippets: list[str] = []
    for sf in result.suggested_files[:_TOP_N_FILES]:
        if sf.path in emitted_files:
            continue
        file_path = root / sf.path
        if not file_path.exists():
            continue
        snippet = _extract_snippet(file_path, 1, _MAX_SNIPPET_LINES)
        if not snippet:
            continue
        lang = _lang(sf.path)
        file_snippets.append(f"\n### `{sf.path}` (score {sf.score})\n\n```{lang}\n{snippet}\n```")
        emitted_files.add(sf.path)

    if file_snippets:
        sections.append("\n## Suggested files\n")
        sections.extend(file_snippets)

    md = "\n".join(sections)
    # Token estimate (rough: 1 token ≈ 4 chars)
    token_estimate = len(md) // 4
    sections.insert(2, f"**Estimated tokens:** ~{token_estimate:,}\n")

    return "\n".join(sections)


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _extract_snippet(file_path: Path, start: int, end: int | None) -> str:
    """Read lines start..end from a file. Caps at _MAX_SNIPPET_LINES."""
    try:
        lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return ""
    start = max(1, start)
    stop = min(len(lines), (end or start + _MAX_SNIPPET_LINES - 1), start + _MAX_SNIPPET_LINES - 1)
    return "\n".join(lines[start - 1 : stop])


def _lang(file_path: str) -> str:
    ext = Path(file_path).suffix.lower()
    return {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".go": "go",
        ".mjs": "javascript",
        ".cjs": "javascript",
    }.get(ext, "")
