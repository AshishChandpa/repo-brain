# repo-brain — Claude Code Instructions

## Read these files first, in order

Before writing any code, read:

1. `README.md` — what the tool does, all CLI commands, artifact schemas, when to re-index
2. `AGENTS.md` — engineering rules, scope limits, validation checklist
3. `src/repo_brain/models.py` — all Pydantic schemas; do not change without reading this first
4. `.repo-brain/REPO_MAP.md` — current snapshot of this repo's symbols, routes, and tests

## What this project is

A local CLI tool (`repo-brain`) that scans Python/FastAPI repositories and generates
structured context artifacts for AI coding agents. It is intentionally simple and
deterministic — no LLMs, no cloud, no vector DB.

## Current scope (v1 + v2 — do not exceed)

These commands exist:

```
repo-brain init                    # create .repo-brain/ and config.json
repo-brain index                   # scan repo, write all artifacts
repo-brain map                     # print Rich summary from artifacts
repo-brain impact <file>           # reverse lookup: what does changing this file affect?
repo-brain context "<task>"        # keyword scoring: what files/symbols are relevant to a task?
repo-brain serve                   # start MCP server on stdio (for Claude Code / Cursor)
```

Do NOT add: skills, embeddings, vector search, Neo4j, UI, cloud sync,
multi-language support, or autonomous agents — those are future phases.

## Key files

| File | Purpose |
|------|---------|
| `src/repo_brain/cli.py` | Typer CLI — entry point for all commands |
| `src/repo_brain/models.py` | Pydantic schemas for all artifacts |
| `src/repo_brain/config.py` | Config load/save for `.repo-brain/config.json` |
| `src/repo_brain/scanner.py` | Filesystem walk + parser orchestration |
| `src/repo_brain/impact.py` | Reverse lookup: who imports, related tests, affected files |
| `src/repo_brain/context.py` | Keyword scoring: extract keywords, score/rank files, symbols, routes, tests |
| `src/repo_brain/mcp_server.py` | MCP server: 6 tool handlers + Server wiring for stdio transport |
| `src/repo_brain/parsers/python_ast.py` | Import + symbol extraction via `ast` |
| `src/repo_brain/parsers/fastapi.py` | FastAPI route decorator detection |
| `src/repo_brain/parsers/pytest.py` | Test file/function/class detection |
| `src/repo_brain/writers/json_writer.py` | Writes JSON artifacts |
| `src/repo_brain/writers/markdown_writer.py` | Writes `REPO_MAP.md` |

## Before finishing any task

```bash
python -m pytest                                             # all 113 tests must pass
repo-brain index && repo-brain map                           # smoke test the CLI
repo-brain impact src/repo_brain/scanner.py                  # smoke test impact
repo-brain context "scan python files and extract symbols"   # smoke test context
repo-brain serve --help                                      # verify serve command registered
```

## Re-index rule

Run `repo-brain index` after changing any of:
- Python files (add / delete / rename)
- FastAPI route decorators
- Class or function names
- Imports
- Test files or test functions
- `config.json`

## Engineering rules

- Keep changes small — one parser, one writer, one command at a time
- Use `ast` module; do not add Tree-sitter unless `ast` provably cannot handle the task
- Every new parser must have a matching test file under `tests/`
- Generated artifacts must be deterministic (same input → same output)
- Do not scan outside the target repository
- Do not store secrets or credentials anywhere

## Virtual environment

```bash
source .venv/bin/activate
# or on Windows:
.venv\Scripts\activate
```

The tool is installed as `repo-brain` via `pip install -e .`