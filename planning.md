You are my AI coding agent for building a project called `repo-brain`.

The goal is to build a local repository context engine that helps AI coding agents understand a codebase with less token waste, less blind file searching, and better impact analysis.

Read the PRD first if it exists in the repository:

* `repo_context_engine_prd.docx`
* `docs/repo_context_engine_prd.md`
* `docs/PRD.md`
* `README.md`

If the PRD is not available, continue from the requirements below.

Do not build everything at once.

Your first job is to build the smallest useful MVP: a local Python/FastAPI repository scanner that generates structured repository context artifacts.

## Product vision

AI coding agents often waste tokens because they repeatedly search files, read unrelated code, lose context in long sessions, and make changes without understanding the real impact radius.

`repo-brain` should eventually become:

1. A local repository indexer
2. A repository context generator
3. A lightweight dependency and symbol graph
4. An MCP server for AI coding agents
5. A set of workflow skills/instructions for safe coding workflows

But for this first implementation, only build the local indexer and repo-map generator.

## First-session scope

Implement only this:

```text
repo-brain init
repo-brain index
repo-brain map
```

The tool should scan a Python/FastAPI codebase and generate:

```text
.repo-brain/
  repo_map.json
  symbols.json
  imports.json
  routes.json
  tests.json
  REPO_MAP.md
```

Do not implement MCP yet.

Do not implement skills yet.

Do not implement embeddings.

Do not implement vector search.

Do not implement Neo4j.

Do not implement a UI.

Do not implement autonomous agents.

Do not implement multi-language support.

Do not use cloud services.

Do not scan outside the target repository.

## Preferred technical stack

Use:

* Python
* Typer for CLI
* Rich for terminal output
* Pydantic for schemas
* pytest for tests
* Python standard `ast` module for parsing

Avoid adding Tree-sitter in the first version unless standard `ast` clearly cannot support the MVP.

Avoid SQLite in the first version unless JSON files become unmanageable.

## Required CLI behavior

### `repo-brain init`

Creates:

```text
.repo-brain/
```

Also creates a default config file:

```text
.repo-brain/config.json
```

Config should include:

```json
{
  "project_name": null,
  "source_roots": ["."],
  "exclude_dirs": [
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    ".repo-brain"
  ],
  "include_extensions": [".py"]
}
```

### `repo-brain index`

Scans the current repository and generates:

```text
.repo-brain/repo_map.json
.repo-brain/symbols.json
.repo-brain/imports.json
.repo-brain/routes.json
.repo-brain/tests.json
.repo-brain/REPO_MAP.md
```

It should detect:

* Python files
* modules/packages
* imports
* classes
* functions
* async functions
* FastAPI route decorators
* pytest test files
* test functions
* rough module boundaries based on folder structure

### `repo-brain map`

Prints a readable terminal summary using Rich.

It should show:

* total Python files
* total classes
* total functions
* total FastAPI routes
* total test files
* detected top-level modules
* path to generated `REPO_MAP.md`

## Data schemas

Create Pydantic models for generated artifacts.

Suggested models:

```python
class FileInfo(BaseModel):
    path: str
    module_path: str | None = None
    line_count: int
    is_test: bool = False

class ImportInfo(BaseModel):
    file_path: str
    module: str
    name: str | None = None
    alias: str | None = None
    level: int = 0

class SymbolInfo(BaseModel):
    file_path: str
    name: str
    symbol_type: Literal["class", "function", "async_function", "method", "async_method"]
    lineno: int
    end_lineno: int | None = None
    parent: str | None = None

class RouteInfo(BaseModel):
    file_path: str
    method: str
    path: str
    function_name: str
    lineno: int

class TestInfo(BaseModel):
    file_path: str
    test_functions: list[str]
    test_classes: list[str]
```

Generated JSON files should be human-readable with indentation.

## FastAPI route detection

Detect decorators like:

```python
@app.get("/users")
@app.post("/documents/upload")
@router.get("/items/{item_id}")
@router.post("/compare")
```

Supported methods:

```text
get
post
put
patch
delete
options
head
```

For v1, it is acceptable to detect only direct string route paths.

Do not try to fully evaluate dynamic route expressions yet.

## Test detection

Detect test files using:

```text
test_*.py
*_test.py
tests/**/*.py
```

Detect test functions:

```python
def test_something():
async def test_something():
```

Detect test classes:

```python
class TestSomething:
```

## Markdown output

Generate `.repo-brain/REPO_MAP.md`.

It should include:

```markdown
# Repository Map

## Summary

- Python files:
- Classes:
- Functions:
- FastAPI routes:
- Test files:

## Top-level Modules

## FastAPI Routes

| Method | Path | Handler | File |
|---|---|---|---|

## Important Files

## Tests

## Notes

This file is generated by repo-brain. Do not manually edit.
```

## Project structure

Before coding, propose a project structure similar to:

```text
repo-brain/
  pyproject.toml
  README.md
  AGENTS.md
  src/
    repo_brain/
      __init__.py
      cli.py
      config.py
      models.py
      scanner.py
      parsers/
        __init__.py
        python_ast.py
        fastapi.py
        pytest.py
      writers/
        __init__.py
        json_writer.py
        markdown_writer.py
  tests/
    test_scanner.py
    test_python_ast.py
    test_fastapi_routes.py
    test_pytest_detection.py
```

Use a `src/` layout.

## Agent behavior rules

Before writing code, show me:

1. Proposed folder structure
2. Implementation plan
3. Data schemas
4. Small commit/checkpoint plan
5. Assumptions

Then wait for my approval before implementing.

When implementing:

* Keep changes small.
* Do not touch unrelated files.
* Do not add unnecessary dependencies.
* Do not generate huge abstractions.
* Do not create a plugin system yet.
* Do not create MCP yet.
* Do not create skills yet.
* Do not create a database yet.
* Prefer boring, testable code.
* Every command should be runnable locally.
* Every parser should have tests.
* Generated artifacts should be deterministic.

## Required repository instruction file

Create an `AGENTS.md` file for future coding agents.

Content should be minimal:

````markdown
# Repo-Brain Development Rules

This project builds a local repository context engine for AI coding agents.

## Current Scope

Build the Python/FastAPI local indexer first.

Do not build MCP, skills, vector search, UI, graph database, or multi-agent orchestration until the local indexer is working.

## Engineering Rules

- Keep changes small.
- Prefer deterministic parsing before LLM-based extraction.
- Use Python `ast` before adding Tree-sitter.
- Generate readable JSON and Markdown artifacts.
- Every command must be testable from the CLI.
- Do not introduce cloud services.
- Do not store secrets.
- Do not scan outside the target repository.

## Validation

Before finishing any task, run:

```bash
python -m pytest
repo-brain index
repo-brain map
````

## MVP Output

The tool should generate:

```text
.repo-brain/
  repo_map.json
  symbols.json
  imports.json
  routes.json
  tests.json
  REPO_MAP.md
```

````

## Acceptance criteria for first implementation

The first implementation is complete only when:

1. `repo-brain init` creates `.repo-brain/config.json`.
2. `repo-brain index` scans a sample Python/FastAPI repo.
3. `repo-brain index` generates all required JSON files.
4. `repo-brain index` generates `REPO_MAP.md`.
5. `repo-brain map` prints a readable summary.
6. FastAPI routes are detected from decorators.
7. Classes and functions are extracted using `ast`.
8. Imports are extracted using `ast`.
9. Test files and test functions are detected.
10. Unit tests exist for the parser behavior.
11. The code passes pytest.
12. The implementation avoids MCP, skills, embeddings, vector DB, Neo4j, UI, and cloud services.

## Future phases, not for this session

Keep these in mind but do not implement now:

### Phase 2

Add impact analysis:

```bash
repo-brain impact src/services/document_service.py
````

Expected result:

* related imports
* related tests
* related routes
* likely affected files

### Phase 3

Add task context builder:

```bash
repo-brain context "add audit logging to document upload"
```

Expected result:

* likely modules
* files to read
* related symbols
* suggested tests

### Phase 4

Add MCP server exposing tools:

```text
repo_brain_status
repo_brain_search_symbol
repo_brain_related_files
repo_brain_impact
repo_brain_tests
repo_brain_task_context
```

### Phase 5

Add workflow skills/instructions:

* impact-analysis skill
* safe-refactor skill
* bug-investigation skill
* test-coverage skill
* feature-implementation skill

## Final instruction

Do not over-engineer.

The goal of v1 is not to build a perfect knowledge graph.

The goal of v1 is to prove this simple loop:

```text
scan repository
  ↓
generate structured repo context
  ↓
help AI agents read fewer irrelevant files
```

Start by showing me the plan and proposed structure. Do not write code until I approve the plan.
