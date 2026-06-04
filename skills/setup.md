# Skill: Setup / Session Start

Run this skill at the **start of every coding session** on a repository.
It ensures repo-brain is initialised, the index is fresh, and the agent
has a full picture of the codebase before touching anything.

Install as a Claude Code slash command:
```bash
cp /path/to/repo-brain/skills/setup.md .claude/commands/setup.md
```

Then type `/setup` at the start of any session.

---

## What this skill does

1. Checks whether repo-brain is already initialised
2. Initialises it if not (runs `init` + `index`)
3. Re-indexes if the index is stale or missing
4. Shows the current repository map
5. Asks what you want to work on
6. Runs `context` for your task and shows you exactly where to start

---

## Steps

### 1. Check if repo-brain is initialised

Look for a `.repo-brain/` directory in the repository root.

**If `.repo-brain/` does not exist:**

```
CLI: repo-brain init
```

Then go to Step 2.

**If `.repo-brain/` exists but `repo_map.json` is missing:**

```
CLI: repo-brain index
```

Then go to Step 3.

**If `.repo-brain/repo_map.json` exists:**

Go to Step 2 to check freshness.

---

### 2. Check if the index is fresh

```
CLI:  repo-brain map
MCP:  repo_brain_status()
```

Read the `Scanned at` timestamp.

- If scanned **less than 1 hour ago** and no new files have been added → index is fresh, go to Step 3.
- If scanned **more than 1 hour ago**, or if you know files have changed since the last scan → re-index now:

```
CLI: repo-brain index
```

After indexing, run `repo-brain map` once more to confirm.

---

### 3. Show the repository overview

Print a summary for the user:

```
CLI:  repo-brain map
MCP:  repo_brain_status()
```

Tell the user:
- How many Python files, classes, functions, routes, and test files exist
- Which top-level modules were detected
- When the index was last updated

Example output to share:

```
Repository is indexed and ready.

  Python files   41
  Classes        28
  Functions      284
  FastAPI routes 18
  Test files     9
  Modules        app, tests
  Last indexed   2026-06-04T10:30:00+00:00
```

---

### 4. Ask what the user wants to work on

Ask this question exactly:

> "What would you like to work on today? Describe the task or bug in one or two sentences."

Wait for the user's answer before continuing.

---

### 5. Run context for the task

Take the user's answer from Step 4 and run:

```
CLI:  repo-brain context "<user's task>"
MCP:  repo_brain_task_context(task="<user's task>")
```

Present the results clearly:

- **Start by reading these files** (top suggested files, highest score first)
- **Key symbols to look at** (top suggested symbols with file:line)
- **Routes involved** (if any FastAPI routes matched)
- **Tests to keep passing** (suggested test files)

---

### 6. Confirm the starting point

Tell the user:

> "Based on the index, here is where I suggest we start:
> - Read: `<top file>`
> - Key symbol: `<top symbol>` at `<file>:<line>`
> - Tests to watch: `<test file>`
>
> Should I open `<top file>` and walk through the relevant section?"

Wait for confirmation before opening any files.

---

## What good setup output looks like

```
Checking repo-brain status...

✓ .repo-brain/ found
✓ Index is fresh (scanned 12 minutes ago)

Repository overview:
  Python files   41  |  Routes  18
  Classes        28  |  Tests    9
  Functions     284  |  Modules  app, tests

What would you like to work on today?

> "Add rate limiting to the document upload endpoint"

Running context analysis...

Start by reading:
  app/routes/documents.py          ████ score 4
  app/services/document_service.py ███  score 3
  app/middleware/                  █    score 1

Key symbols:
  upload_document  app/routes/documents.py:28
  DocumentService  app/services/document_service.py:12

Routes involved:
  POST /documents/upload → upload_document

Tests to keep passing:
  tests/test_documents_routes.py
  tests/test_document_service.py

Ready. Shall I open app/routes/documents.py?
```

---

## Safety rules

- Do not open any file, write any code, or make any suggestion until Steps 1–3
  are complete and the index is confirmed fresh
- Do not skip Step 4 — always ask what the user wants to work on
- Do not assume the task from prior conversation context; ask fresh each session
- If `repo-brain index` fails (e.g. no Python files found), tell the user and
  ask them to check the `source_roots` in `.repo-brain/config.json`

---

## Quick reference

| Situation | Action |
|-----------|--------|
| First time on this repo | `repo-brain init` → `repo-brain index` → `repo-brain map` |
| Index exists, less than 1h old | `repo-brain map` only |
| Index exists, more than 1h old | `repo-brain index` → `repo-brain map` |
| Files added since last index | `repo-brain index` → `repo-brain map` |
| MCP connected | Use `repo_brain_status()` instead of `repo-brain map` |
