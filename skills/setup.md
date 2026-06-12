# Skill: Setup / Session Start

Run this skill at the **start of every coding session** on a repository.
It ensures repo-brain is initialised, the index is fresh, and the agent
has a full picture of the codebase before touching anything.

Install as a Claude Code slash command:
```bash
repo-brain setup-project    # installs all skills automatically
```

Then type `/setup` at the start of any session.

---

## What this skill does

1. Checks whether repo-brain is initialised
2. Initialises and indexes if not
3. Re-indexes if stale (incremental — only changed files re-parsed)
4. Shows the current repository map
5. Runs a test-gap check and surfaces untested symbols
6. Asks what you want to work on
7. Runs `context` (with git-diff boost if on a feature branch) and shows where to start

---

## Steps

### 1. Check if repo-brain is initialised

Look for a `.repo-brain/` directory in the repository root.

**If `.repo-brain/` does not exist:**

```
CLI: repo-brain setup-project
```

This runs init + index + installs skills + registers MCP in one command.
Then continue from Step 3.

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
- If scanned **more than 1 hour ago**, or if you know files have changed since the last scan → re-index:

```
CLI: repo-brain index          # incremental by default — only changed files re-parsed
CLI: repo-brain index --force  # full re-scan if something seems wrong
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
- How many files, classes, functions, routes, and test files exist (by language)
- Call graph edge count (deeper impact analysis)
- When the index was last updated

Example:

```
Repository is indexed and ready.

  Files        41  (python: 38  node: 3)
  Classes      28    Functions    284
  Routes       18    Test files     9
  Call edges  412    Route links    6
  Last indexed 2026-06-12T10:30:00+00:00
```

---

### 3.5. Check for test gaps

Run a quick gaps check to surface untested symbols:

```
CLI:  repo-brain gaps
MCP:  repo_brain_gaps()
```

If gaps are found, mention the count to the user:
> "Found 12 untested symbols — run `repo-brain gaps` to see the full list, or `/test-coverage` to add coverage."

Do not block on this — it's informational.

---

### 4. Ask what the user wants to work on

Ask this question exactly:

> "What would you like to work on today? Describe the task or bug in one or two sentences."

Wait for the user's answer before continuing.

---

### 5. Run context for the task

Take the user's answer from Step 4. If there are uncommitted changes or you're on a feature branch, also run with `--since` to boost recently changed files:

```
CLI:  repo-brain context "<user's task>"
CLI:  repo-brain context "<user's task>" --since HEAD     # boost uncommitted changes
MCP:  repo_brain_task_context(task="<user's task>")
```

Present the results clearly:

- **Start by reading these files** (top suggested files, highest score first; `[diff]` tag if recently changed)
- **Key symbols to look at** (top suggested symbols with file:line)
- **Routes involved** (if any routes matched)
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
  Files   41 (python: 38)  |  Routes       18
  Classes 28               |  Tests          9
  Functions 284            |  Call edges   412

Test gaps: 5 untested symbols (run repo-brain gaps to see list)

What would you like to work on today?

> "Add rate limiting to the document upload endpoint"

Running context analysis...

Start by reading:
  app/routes/documents.py          ████ score 4  [diff]
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

## Power features to mention when relevant

| Need | Command |
|------|---------|
| Keep index live while coding | `repo-brain watch` (auto re-indexes on file save) |
| Paste code into AI context | `repo-brain export "your task"` → Markdown with real code snippets |
| See untested symbols | `repo-brain gaps` or `repo_brain_gaps()` |
| Context for recent changes | `repo-brain context "task" --since main` |
| Deep call-graph impact | `repo-brain impact <file>` — includes call-graph callers |
| Frontend↔backend links | `repo_brain_route_links()` |

---

## Safety rules

- Do not open any file, write any code, or make any suggestion until Steps 1–3 are complete
- Do not skip Step 4 — always ask what the user wants to work on
- Do not assume the task from prior conversation context; ask fresh each session
- If `repo-brain index` fails (e.g. no files found), tell the user to check `source_roots` in `.repo-brain/config.json`
- For long sessions, suggest `repo-brain watch` in a background terminal

---

## Quick reference

| Situation | Action |
|-----------|--------|
| First time on this repo | `repo-brain setup-project` |
| Index exists, less than 1h old | `repo-brain map` only |
| Index exists, more than 1h old | `repo-brain index` → `repo-brain map` |
| Working on a long task | Start `repo-brain watch` in background terminal |
| Need actual code in context | `repo-brain export "<task>"` |
| MCP connected | Use `repo_brain_status()` instead of CLI |
