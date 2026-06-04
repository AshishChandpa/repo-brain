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
```

## When to re-index

Re-run `repo-brain index` after any of these changes:

- Added, deleted, or renamed a Python file or directory
- Added, changed, or removed a FastAPI route decorator
- Added, renamed, or removed a class or function
- Added or changed an import
- Added or removed a test file or test function
- Changed `config.json` (source roots, exclusions)

You do NOT need to re-index after:

- Changing logic inside a function body (no symbol/route change)
- Changing comments or docstrings only

One-liner to re-index and verify:

```bash
repo-brain index && repo-brain map
```

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
