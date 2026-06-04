# PRD

The canonical product requirements document is:

[`docs/repo_context_engine_prd.md`](./repo_context_engine_prd.md)

Use that file as the source of truth.

## Current Product Direction

Repo-Brain is a local repository context engine for AI coding agents.

The goal is to reduce token waste, repeated file searching, and poor codebase understanding by generating structured repository context artifacts.

## Current MVP

The first version should only build:

```bash
repo-brain init
repo-brain index
repo-brain map
```

The MVP should generate:

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

## Current Non-Goals

Do not build these in v1:

* MCP server
* skills
* vector database
* embeddings
* Neo4j
* UI
* cloud sync
* multi-agent orchestration
* multi-language support

For full details, read:

[`docs/repo_context_engine_prd.md`](./repo_context_engine_prd.md)
