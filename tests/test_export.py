import tempfile
from pathlib import Path

from repo_brain.export import _extract_snippet, _lang, export_context


# ---------------------------------------------------------------------------
# _extract_snippet
# ---------------------------------------------------------------------------

def test_extract_snippet_basic():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("line1\nline2\nline3\nline4\nline5\n")
        path = Path(f.name)
    snippet = _extract_snippet(path, 2, 4)
    assert "line2" in snippet
    assert "line4" in snippet
    assert "line5" not in snippet


def test_extract_snippet_single_line():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("only line\n")
        path = Path(f.name)
    snippet = _extract_snippet(path, 1, 1)
    assert snippet == "only line"


def test_extract_snippet_missing_file():
    snippet = _extract_snippet(Path("/nonexistent/file.py"), 1, 10)
    assert snippet == ""


def test_extract_snippet_caps_at_max_lines():
    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write("\n".join(f"line{i}" for i in range(200)))
        path = Path(f.name)
    snippet = _extract_snippet(path, 1, None)
    lines = snippet.splitlines()
    assert len(lines) <= 60


# ---------------------------------------------------------------------------
# _lang
# ---------------------------------------------------------------------------

def test_lang_python():
    assert _lang("app/main.py") == "python"


def test_lang_typescript():
    assert _lang("src/index.ts") == "typescript"


def test_lang_go():
    assert _lang("cmd/main.go") == "go"


def test_lang_unknown():
    assert _lang("file.txt") == ""


# ---------------------------------------------------------------------------
# export_context integration (light — uses temp dir with minimal artifacts)
# ---------------------------------------------------------------------------

def test_export_context_returns_markdown():
    with tempfile.TemporaryDirectory() as tmpdir:
        root = Path(tmpdir)
        brain_dir = root / ".repo-brain"
        brain_dir.mkdir()

        # Write minimal artifacts
        import json
        (brain_dir / "symbols.json").write_text(json.dumps([
            {
                "file_path": "app/users.py",
                "name": "get_user",
                "symbol_type": "function",
                "lineno": 1,
                "end_lineno": 5,
                "parent": None,
            }
        ]))
        (brain_dir / "routes.json").write_text("[]")
        (brain_dir / "imports.json").write_text("[]")
        (brain_dir / "tests.json").write_text("[]")

        # Create a minimal source file
        (root / "app").mkdir()
        (root / "app" / "users.py").write_text("def get_user(user_id):\n    return None\n")

        md = export_context("get user by id", brain_dir, root)

    assert "# Context export" in md
    assert "get_user" in md or "Keywords" in md