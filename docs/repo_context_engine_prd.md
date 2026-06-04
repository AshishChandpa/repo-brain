# Repo-Brain PRD: Repository Context Engine for AI Coding Agents

## 1. Overview

Repo-Brain is a local repository context engine that helps AI coding agents understand software projects with less token waste, less blind file searching, and better change-impact awareness.

The initial version focuses only on Python/FastAPI repositories. It scans a local codebase and generates structured artifacts such as repository maps, symbols, imports, routes, tests, and Markdown summaries.

The long-term direction is to expose this repository intelligence through CLI commands, MCP tools, and workflow-specific AI agent skills.

## 2. Problem Statement

AI coding agents often struggle with medium and large codebases because they discover context inefficiently.

Common failure patterns:

* Repeatedly searching the same files
* Reading too many unrelated files
* Losing context in long sessions
* Making edits without understanding affected routes, tests, or dependencies
* Burning excessive input tokens
* Producing slower and lower-quality output as context grows

The issue is not only model intelligence. The deeper issue is poor repository context management.

## 3. Why This Problem Exists

Most coding agents interact with codebases through generic file operations:

* list files
* search text
* open file
* inspect output
* repeat

This creates a reactive workflow. The agent discovers architecture only after spending tokens and tool calls.

A better workflow is:

```text
scan repository
  ↓
build structured context
  ↓
answer repository questions from artifacts
  ↓
open fewer, more relevant files
```

## 4. Target Users

Primary users:

* Backend engineers working in Python/FastAPI codebases
* Developers using Claude Code, Codex, Cursor, GitHub Copilot, or OpenCode
* Engineers working on repositories where AI agents waste time exploring files

Secondary users:

* Tech leads reviewing change impact
* Teams trying to standardize AI-assisted development
* Developers building MCP-based coding tools

## 5. Product Strategy

The product should start as a boring, deterministic local tool.

The v1 strategy is:

1. Build a local indexer first
2. Generate JSON and Markdown artifacts
3. Keep outputs human-readable
4. Avoid LLM-based extraction initially
5. Avoid graph databases and vector databases initially
6. Add MCP only after the local artifacts are reliable
7. Add skills only after the MCP tool behavior is useful

## 6. MVP Scope

The first MVP includes only:

```bash
repo-brain init
repo-brain index
repo-brain map
```

The MVP scans a Python/FastAPI repository and generates:

```text
.repo-brain/
  config.json
  repo_map.json
  symbols.json
  imports.json
  routes.json
  tests.json
  REPO_MAP.md
```

## 7. Out of Scope for MVP

Do not build these in v1:

* MCP server
* AI skills
* Vector database
* Embeddings
* Neo4j
* Cloud sync
* UI/dashboard
* Multi-agent orchestration
* Autonomous PR generation
* Multi-language support
* LLM-based code summarization

## 8. Functional Requirements

### `repo-brain init`

Creates `.repo-brain/` and `.repo-brain/config.json`.

Default config:

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

Scans the current repository and extracts:

* Python files
* modules/packages
* imports
* classes
* functions
* async functions
* FastAPI routes
* pytest test files
* test functions
* rough module boundaries from folder structure

It generates JSON and Markdown artifacts under `.repo-brain/`.

### `repo-brain map`

Prints a readable terminal summary:

* total Python files
* total classes
* total functions
* total FastAPI routes
* total test files
* top-level modules
* path to generated `REPO_MAP.md`

## 9. Data Artifacts

### `repo_map.json`

High-level repository inventory.

Should include:

* project name
* scan timestamp
* Python file count
* top-level folders/modules
* generated artifact paths

### `symbols.json`

Detected classes, functions, async functions, methods, and async methods.

### `imports.json`

Detected imports from Python AST parsing.

### `routes.json`

Detected FastAPI routes from decorators.

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

### `tests.json`

Detected test files, test functions, and test classes.

### `REPO_MAP.md`

Human-readable repository map intended for developers and AI coding agents.

## 10. Recommended Technical Stack

Use:

* Python
* Typer for CLI
* Rich for terminal output
* Pydantic for schemas
* pytest for tests
* Python standard `ast` module for parsing

Avoid Tree-sitter until the standard AST parser is insufficient.

Avoid SQLite until JSON artifacts become too limited.

## 11. Future Phases

### Phase 2: Impact Analysis

Add:

```bash
repo-brain impact src/services/document_service.py
```

Expected output:

* related imports
* related tests
* related routes
* likely affected files

### Phase 3: Task Context Builder

Add:

```bash
repo-brain context "add audit logging to document upload"
```

Expected output:

* likely modules
* files to read
* related symbols
* suggested tests

### Phase 4: MCP Server

Expose tools:

```text
repo_brain_status
repo_brain_search_symbol
repo_brain_related_files
repo_brain_impact
repo_brain_tests
repo_brain_task_context
```

### Phase 5: Skills and Agent Workflows

Add workflow skills:

* impact-analysis skill
* safe-refactor skill
* bug-investigation skill
* test-coverage skill
* feature-implementation skill

## 12. Success Metrics

MVP success means:

* The tool runs locally without cloud dependencies
* The CLI works on a real Python/FastAPI repository
* Generated artifacts are deterministic
* Generated Markdown is readable
* FastAPI routes are detected
* imports, classes, and functions are extracted
* tests are detected
* the tool reduces manual file exploration for common tasks

Future success metrics:

* fewer files opened by AI agents
* fewer repeated searches
* lower token usage
* faster task completion
* better test targeting
* safer refactors

## 13. Risks

Main risks:

* Overengineering too early
* Poor FastAPI route detection
* False confidence from incomplete static analysis
* Generated artifacts becoming stale
* AI agents ignoring generated context
* Context files becoming too large and harming performance

## 14. Design Principles

* Local-first
* Deterministic before AI-generated
* Human-readable artifacts
* Small CLI surface
* No cloud dependency
* No graph database in v1
* No vector database in v1
* Build one useful vertical slice first

## 15. Open Questions

* Should Tree-sitter replace Python AST in phase 2?
* Should SQLite become the default storage layer?
* How should incremental indexing work?
* How should generated repo context be consumed by Claude Code, Codex, Copilot, Cursor, and OpenCode?
* What is the smallest useful MCP tool set?
* Should skills be tool-specific or generic Markdown workflows?
