# ContextGraph Workspace — Claude Code Instructions

## Read these files first, in order

1. `docs/repo_context_engine_prd.md` — full product requirements (source of truth)
2. `planning.md` — session-by-session implementation plan and agent rules
3. `repo-brain/CLAUDE.md` — detailed instructions for the repo-brain tool itself
4. `repo-brain/README.md` — CLI usage, artifact schemas, re-index rules

## What this workspace is

This is the development workspace for **repo-brain** — a local repository context
engine that helps AI coding agents understand codebases with less token waste.

The actual tool code lives in `repo-brain/`. Everything else here is planning and
product documentation.

## Workspace layout

```
ContextGraph/
  CLAUDE.md                          ← you are here
  README.md                          ← project overview pointer
  planning.md                        ← agent session instructions
  docs/
    PRD.md                           ← pointer to canonical PRD
    repo_context_engine_prd.md       ← canonical PRD (read this)
  repo-brain/                        ← the actual tool
    CLAUDE.md                        ← Claude instructions for the tool
    README.md                        ← tool usage docs
    AGENTS.md                        ← engineering rules
    pyproject.toml
    src/repo_brain/                  ← source code
    tests/                           ← pytest tests
    .repo-brain/                     ← generated artifacts (index of itself)
```

## Current implementation status

### Done (v1)

- `repo-brain init` — creates `.repo-brain/config.json`
- `repo-brain index` — scans repo, writes all 6 artifacts
- `repo-brain map` — prints Rich terminal summary
- Parsers: imports, symbols, FastAPI routes, pytest tests (all via `ast`)
- 33 passing tests
- README, AGENTS.md, CLAUDE.md

### Not started

| Phase | Command | Description |
|-------|---------|-------------|
| v2 | `repo-brain impact <file>` | Show affected routes, tests, imports for a file |
| v3 | `repo-brain context "<task>"` | Suggest files/symbols relevant to a task description |
| v4 | MCP server | Expose repo context as tools for Claude Code, Cursor, Copilot |
| v5 | Skills | Workflow instructions: safe-refactor, bug-investigation, etc. |

## Rules for this workspace

- The PRD (`docs/repo_context_engine_prd.md`) is the source of truth — do not contradict it
- Do not start Phase 2+ without completing and validating Phase 1 first
- Do not build MCP, skills, vector DB, embeddings, or UI until the local indexer is reliable
- All implementation happens inside `repo-brain/` — do not create new top-level packages

## When starting a new session

1. Read this file (`CLAUDE.md`)
2. Read `docs/repo_context_engine_prd.md`
3. Read `repo-brain/CLAUDE.md`
4. Run `cd repo-brain && python -m pytest` to confirm current state
5. Run `repo-brain index && repo-brain map` to see the current repo snapshot