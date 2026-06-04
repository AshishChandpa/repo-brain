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

## Current implementation status — all phases complete

| Phase | Feature | Status |
|-------|---------|--------|
| v1 | `init` / `index` / `map` + JSON/MD artifacts, 113 tests | Done |
| v2 | `repo-brain impact <file>` — reverse import + test lookup | Done |
| v3 | `repo-brain context "<task>"` — keyword-scored suggestions | Done |
| v4 | `repo-brain serve` — MCP server, 6 tools for Claude Code / Cursor | Done |
| v5 | `skills/` — 5 Markdown workflow skills as Claude Code slash commands | Done |

## What each v1 command does

- `repo-brain init` — creates `.repo-brain/config.json`
- `repo-brain index` — scans repo, writes 8 artifacts (JSON + MD + last_impact + last_context)
- `repo-brain map` — prints Rich terminal summary from artifacts
- `repo-brain impact <file>` — reverse lookup: importers, tests, affected files
- `repo-brain context "<task>"` — keyword scoring: ranked files, symbols, routes, tests
- `repo-brain serve` — stdio MCP server exposing 6 tools to AI agents

## Skills (install as Claude Code slash commands)

```bash
cp repo-brain/skills/*.md .claude/commands/
```

| Skill | When to use |
|-------|-------------|
| `/impact-analysis` | Before touching any file |
| `/safe-refactor` | Renaming or moving code |
| `/bug-investigation` | Debugging a failure |
| `/test-coverage` | Finding and filling test gaps |
| `/feature-implementation` | Starting a new feature |

## Rules for this workspace

- The PRD (`docs/repo_context_engine_prd.md`) is the source of truth
- All implementation happens inside `repo-brain/` — do not create new top-level packages
- Do not add embeddings, vector DB, Neo4j, cloud sync, or UI

## When starting a new session

1. Read this file (`CLAUDE.md`)
2. Read `docs/repo_context_engine_prd.md`
3. Read `repo-brain/CLAUDE.md`
4. Run `cd repo-brain && python -m pytest` to confirm current state
5. Run `repo-brain index && repo-brain map` to see the current repo snapshot