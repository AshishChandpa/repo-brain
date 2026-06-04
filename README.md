# repo-brain

A local repository context engine for AI coding agents.

Scans a Python/FastAPI codebase and generates structured context artifacts — so AI agents spend fewer tokens searching files and more time doing useful work.

---

## What it does

```
scan repository
  ↓
generate structured context
  ↓
AI agents read fewer irrelevant files
```

It produces these files under `.repo-brain/`:

| File | What it contains |
|------|-----------------|
| `config.json` | Scan settings (roots, exclusions, extensions) |
| `repo_map.json` | Project-level summary: file count, modules, timestamps |
| `symbols.json` | Every class, function, method, and async variant |
| `imports.json` | Every import statement across all Python files |
| `routes.json` | FastAPI route decorators (`@app.get`, `@router.post`, …) |
| `tests.json` | Test files, test functions, and test classes |
| `REPO_MAP.md` | Human-readable summary of everything above |
| `last_impact.json` | Result of the most recent `impact` run |

---

## Installation

Requires Python 3.11+.

```bash
# Clone / navigate to repo-brain
cd repo-brain

# Create a virtual environment
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# Install in editable mode
pip install -e .
```

To verify the install:

```bash
repo-brain --help
```

---

## Quick start

```bash
repo-brain init                              # creates .repo-brain/ and config.json
repo-brain index                             # scans the repo and writes all artifacts
repo-brain map                               # prints a Rich summary table in the terminal
repo-brain impact src/services/users.py      # show what breaks if this file changes
```

---

## Commands

### `repo-brain impact <file>`

Answers: *"If I change this file, what else is affected?"*

Reads existing `.repo-brain/` artifacts (no re-scan needed) and performs reverse lookups.

```bash
repo-brain impact src/services/users.py
repo-brain impact src/services/users.py --root /path/to/repo
```

Shows:
- **Symbols defined in the file** — classes, functions, methods (with line numbers)
- **FastAPI routes defined in the file** — method, path, handler
- **Imported by** — other files that import this module
- **Related tests** — test files that import this module or match `test_<stem>.py`
- **Likely affected files** — sorted union of all the above

Also writes `.repo-brain/last_impact.json` for agent consumption.

**Requires `repo-brain index` to have been run first.**

---

### `repo-brain init`

Creates `.repo-brain/` and writes a default `config.json`.

```bash
repo-brain init
repo-brain init --root /path/to/repo    # non-CWD target
```

Default `config.json`:

```json
{
  "project_name": null,
  "source_roots": ["."],
  "exclude_dirs": [
    ".git", ".venv", "venv", "__pycache__",
    ".mypy_cache", ".pytest_cache", "node_modules", ".repo-brain"
  ],
  "include_extensions": [".py"]
}
```

Edit this file before running `index` if you want to:
- Set a `project_name`
- Add extra `exclude_dirs`
- Change `source_roots` (e.g. `["src"]` for a `src/` layout)

---

### `repo-brain index`

Scans the repository and (re)generates all artifacts.

```bash
repo-brain index
repo-brain index --root /path/to/repo
```

Detects:
- Python files, line counts, module paths
- Imports (`import x`, `from x import y`, relative imports)
- Classes, functions, async functions, methods, async methods
- FastAPI route decorators for `get post put patch delete options head`
- Test files (`test_*.py`, `*_test.py`), test functions (`test_*`), test classes (`Test*`)

**Run this every time you change the codebase** — see [When to re-index](#when-to-re-index).

---

### `repo-brain map`

Reads existing `.repo-brain/` artifacts and prints a terminal summary.

```bash
repo-brain map
repo-brain map --root /path/to/repo
```

Does not re-scan. Shows:
- Python file count, class count, function count
- FastAPI route count, test file count
- Top-level modules
- Path to `REPO_MAP.md`

---

## When to re-index

`.repo-brain/` artifacts are a **snapshot** — they go stale when the code changes.
Re-run `repo-brain index` after any of these:

| Change | Re-index needed? |
|--------|-----------------|
| Added a new Python file | Yes |
| Deleted a Python file | Yes |
| Added or removed a FastAPI route | Yes |
| Added or renamed a function or class | Yes |
| Added a new import | Yes |
| Added or removed a test | Yes |
| Changed only logic inside a function body | No — symbols/routes are unchanged |
| Changed a config value in `config.json` | Yes |
| Renamed a module or directory | Yes |

### One-liner to re-index and verify

```bash
repo-brain index && repo-brain map
```

### Hook it into your workflow (optional)

Add a `Makefile` target so you never forget:

```makefile
.PHONY: index
index:
	repo-brain index && repo-brain map
```

Or a pre-commit hook (`.git/hooks/pre-commit`):

```bash
#!/bin/sh
repo-brain index
git add .repo-brain/
```

---

## Generated artifacts

### `.repo-brain/repo_map.json`

```json
{
  "project_name": null,
  "scan_timestamp": "2026-06-04T09:31:56.674772+00:00",
  "python_file_count": 12,
  "top_level_modules": ["app", "tests"],
  "artifact_paths": { ... }
}
```

### `.repo-brain/symbols.json`

```json
[
  {
    "file_path": "app/routes/users.py",
    "name": "UserService",
    "symbol_type": "class",
    "lineno": 10,
    "end_lineno": 45,
    "parent": null
  },
  {
    "file_path": "app/routes/users.py",
    "name": "get_user",
    "symbol_type": "async_method",
    "lineno": 18,
    "end_lineno": 25,
    "parent": "UserService"
  }
]
```

`symbol_type` values: `class` `function` `async_function` `method` `async_method`

### `.repo-brain/imports.json`

```json
[
  {
    "file_path": "app/main.py",
    "module": "fastapi",
    "name": "FastAPI",
    "alias": null,
    "level": 0
  },
  {
    "file_path": "app/services/users.py",
    "module": "models",
    "name": "User",
    "alias": null,
    "level": 1
  }
]
```

`level`: `0` = absolute import, `1` = relative (`from . import`), `2` = parent (`from .. import`), etc.

### `.repo-brain/routes.json`

```json
[
  {
    "file_path": "app/routes/users.py",
    "method": "get",
    "path": "/users/{user_id}",
    "function_name": "get_user",
    "lineno": 18
  }
]
```

### `.repo-brain/tests.json`

```json
[
  {
    "file_path": "tests/test_users.py",
    "test_functions": ["test_get_user", "TestUserRoutes.test_create"],
    "test_classes": ["TestUserRoutes"]
  }
]
```

### `.repo-brain/REPO_MAP.md`

Human-readable Markdown. Safe to commit. Useful to paste into AI agent context.

---

## Project layout

```
repo-brain/
  pyproject.toml
  README.md
  AGENTS.md                     ← rules for AI coding agents working on this repo
  src/
    repo_brain/
      cli.py                    ← Typer commands: init, index, map
      config.py                 ← Config schema + load/save
      models.py                 ← Pydantic schemas for all artifacts
      scanner.py                ← filesystem walk + parser orchestration
      parsers/
        python_ast.py           ← imports + symbols via stdlib ast
        fastapi.py              ← route decorator detection
        pytest.py               ← test file/function/class detection
      writers/
        json_writer.py          ← writes the five JSON artifacts
        markdown_writer.py      ← writes REPO_MAP.md
  tests/
    test_python_ast.py
    test_fastapi_routes.py
    test_pytest_detection.py
    test_scanner.py
```

---

## Development

```bash
# Run tests
python -m pytest

# Run tests with output
python -m pytest -v

# Index this repo itself (useful as a smoke test)
repo-brain index && repo-brain map
```

All tests must pass before committing. Every parser module has a corresponding test file.

---

## Limitations (v1)

- Python only — no TypeScript, Go, or other languages
- FastAPI route detection requires a literal string path argument; dynamic paths like `@router.get(PREFIX + "/users")` are skipped
- No incremental indexing — every `index` run is a full scan
- No MCP server, no embeddings, no vector search (planned for later phases)

---

## Roadmap

| Phase | Feature | Status |
|-------|---------|--------|
| v1 | `init` / `index` / `map`, JSON + Markdown artifacts | Done |
| v2 | `repo-brain impact <file>` — show affected routes, tests, imports | Done |
| v3 | `repo-brain context "<task>"` — suggest files and symbols for a task | Next |
| v4 | MCP server exposing repo context as tools | Planned |
| v5 | AI agent workflow skills (safe-refactor, bug-investigation, …) | Planned |