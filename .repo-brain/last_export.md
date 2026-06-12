# Context export: add test gap detection to CLI

**Keywords:** test, gap, detection, cli

**Estimated tokens:** ~2,688


## Tests to run

- `tests/test_call_graph.py`
- `tests/test_context.py`
- `tests/test_export.py`
- `tests/test_fastapi_routes.py`
- `tests/test_gaps.py`

## Key symbols


### `test_is_test_file_prefix` (function) — tests/test_pytest_detection.py:28

```python
def test_is_test_file_prefix():
    assert is_test_file("test_scanner.py") is True
```

### `test_is_test_file_suffix` (function) — tests/test_pytest_detection.py:32

```python
def test_is_test_file_suffix():
    assert is_test_file("scanner_test.py") is True
```

### `test_is_not_test_file` (function) — tests/test_pytest_detection.py:36

```python
def test_is_not_test_file():
    assert is_test_file("scanner.py") is False
    assert is_test_file("routes.py") is False
```

### `test_detects_test_functions` (function) — tests/test_pytest_detection.py:41

```python
def test_detects_test_functions():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "test_something" in info.test_functions
    assert "test_async_thing" in info.test_functions
```

### `test_detects_test_class` (function) — tests/test_pytest_detection.py:47

```python
def test_detects_test_class():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "TestMyFeature" in info.test_classes
```

### `test_detects_methods_in_test_class` (function) — tests/test_pytest_detection.py:52

```python
def test_detects_methods_in_test_class():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "TestMyFeature.test_works" in info.test_functions
```

### `test_ignores_helper_function` (function) — tests/test_pytest_detection.py:57

```python
def test_ignores_helper_function():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "helper" not in info.test_functions
```

### `test_ignores_non_test_class` (function) — tests/test_pytest_detection.py:62

```python
def test_ignores_non_test_class():
    info = parse_tests("test_sample.py", TEST_SOURCE)
    assert "NotATestClass" not in info.test_classes
```

## Suggested files


### `src/repo_brain/cli.py` (score 1)

```python
from __future__ import annotations

import importlib.resources as pkg_resources
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from repo_brain.config import Config, brain_dir, load_config, save_config
from repo_brain.context import build_context, get_diff_files, load_context_artifacts
from repo_brain.export import export_context
from repo_brain.gaps import find_gaps, load_gaps_artifacts
from repo_brain.impact import analyse, load_impact_artifacts
from repo_brain.mcp_server import run_server
from repo_brain.models import RepoMap
from repo_brain.scanner import file_counts_by_language, scan, scan_incremental, top_level_modules
from repo_brain.writers.json_writer import write_artifacts, write_hashes
from repo_brain.writers.markdown_writer import write_markdown

app = typer.Typer(
    name="repo-brain",
    help="Local repository context engine for AI coding agents.",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Initialise .repo-brain/ and create default config.json."""
    bd = brain_dir(root)
    if bd.exists():
        console.print(f"[yellow].repo-brain/ already exists at {bd.resolve()}[/yellow]")
    else:
        bd.mkdir(parents=True)
        console.print(f"[green]Created {bd.resolve()}[/green]")

    config = Config()
    save_config(config, root)
    console.print(f"[green]Config written to {bd / 'config.json'}[/green]")


@app.command()
def index(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
    force: bool = typer.Option(False, "--force", help="Force full re-scan (ignore file hashes)"),
) -> None:
    """Scan the repository and generate context artifacts.

    Uses incremental indexing by default — only re-parses changed files.
    Use --force for a full re-scan.
```

### `tests/test_call_graph.py` (score 1)

```python
"""Tests for call graph extraction across all three language parsers."""
from repo_brain.parsers.python_ast import parse_calls as py_parse_calls
from repo_brain.parsers.node import parse_calls as node_parse_calls, parse_fetch_calls
from repo_brain.parsers.go import parse_calls as go_parse_calls

# ---------------------------------------------------------------------------
# Python call graph
# ---------------------------------------------------------------------------

PY_SOURCE = """
def helper():
    pass

def process_user(user_id):
    data = helper()
    return validate(data)

class UserService:
    def get(self, uid):
        return fetch_user(uid)
"""

def test_py_detects_call_in_function():
    calls = py_parse_calls("app.py", PY_SOURCE)
    callee_names = [c.callee_name for c in calls]
    assert "helper" in callee_names
    assert "validate" in callee_names

def test_py_caller_name_tracked():
    calls = py_parse_calls("app.py", PY_SOURCE)
    process_calls = [c for c in calls if c.caller_name == "process_user"]
    assert any(c.callee_name == "helper" for c in process_calls)

def test_py_method_calls_tracked():
    calls = py_parse_calls("app.py", PY_SOURCE)
    assert any(c.callee_name == "fetch_user" for c in calls)

def test_py_file_path_set():
    calls = py_parse_calls("app/users.py", PY_SOURCE)
    assert all(c.caller_file == "app/users.py" for c in calls)

def test_py_lineno_positive():
    calls = py_parse_calls("app.py", PY_SOURCE)
    assert all(c.lineno > 0 for c in calls)

def test_py_empty_source():
    assert py_parse_calls("app.py", "") == []

def test_py_syntax_error_returns_empty():
    assert py_parse_calls("app.py", "def broken(:\n    pass") == []


# ---------------------------------------------------------------------------
# Node.js call graph
# ---------------------------------------------------------------------------

NODE_SOURCE = """
function validateUser(user) {
    return checkEmail(user.email)
}
```

### `tests/test_context.py` (score 1)

```python
import pytest

from repo_brain.context import (
    _extract_keywords,
    _match_routes,
    _match_tests,
    _score_files,
    _score_symbols,
    _tokenize_path,
    build_context,
)
from repo_brain.models import ImportInfo, RouteInfo, SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

SYMBOLS = [
    SymbolInfo(file_path="app/services/document_service.py", name="DocumentService", symbol_type="class", lineno=5),
    SymbolInfo(file_path="app/services/document_service.py", name="upload_document", symbol_type="function", lineno=20),
    SymbolInfo(file_path="app/services/audit_log.py", name="AuditLog", symbol_type="class", lineno=3),
    SymbolInfo(file_path="app/services/audit_log.py", name="write_audit_entry", symbol_type="function", lineno=15),
    SymbolInfo(file_path="app/models/user.py", name="User", symbol_type="class", lineno=1),
    SymbolInfo(file_path="app/utils/helpers.py", name="format_date", symbol_type="function", lineno=8),
]

ROUTES = [
    RouteInfo(file_path="app/routes/documents.py", method="post", path="/documents/upload", function_name="upload_document", lineno=10),
    RouteInfo(file_path="app/routes/documents.py", method="get", path="/documents/{doc_id}", function_name="get_document", lineno=20),
    RouteInfo(file_path="app/routes/users.py", method="get", path="/users", function_name="list_users", lineno=5),
]

IMPORTS = [
    ImportInfo(file_path="app/routes/documents.py", module="app.services.document_service", level=0),
    ImportInfo(file_path="app/routes/users.py", module="app.models.user", level=0),
]

TESTS = [
    TestInfo(file_path="tests/test_document_service.py", test_functions=["test_upload_document", "test_get_document"], test_classes=[]),
    TestInfo(file_path="tests/test_audit_log.py", test_functions=["test_write_audit_entry"], test_classes=[]),
    TestInfo(file_path="tests/test_users.py", test_functions=["test_list_users"], test_classes=[]),
]


# ---------------------------------------------------------------------------
# _extract_keywords
# ---------------------------------------------------------------------------

def test_keywords_lowercased():
    kws = _extract_keywords("Add Audit Logging")
    assert all(k == k.lower() for k in kws)

def test_keywords_removes_stopwords():
    kws = _extract_keywords("add audit logging to document upload")
    assert "add" not in kws
    assert "to" not in kws
    assert "audit" in kws
    assert "logging" in kws
    assert "document" in kws
    assert "upload" in kws
```

### `tests/test_export.py` (score 1)

```python
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
```