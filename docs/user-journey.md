# User Journey: repo-brain

A walkthrough of how a developer uses repo-brain from first install through
daily workflow — on a real Python/FastAPI project.

---

## The situation

You are working on a mid-size FastAPI backend. It has grown to ~40 Python files,
three routers, a service layer, and a test suite. You have just been handed a
ticket:

> "Add audit logging every time a document is uploaded."

You open Claude Code. Without repo-brain, the agent starts reading random files.
With repo-brain, it knows exactly where to look before touching anything.

---

## Step 1 — Install repo-brain

```bash
pip install repo-brain
```

Verify it works:

```bash
repo-brain --help
```

```
Usage: repo-brain [OPTIONS] COMMAND [ARGS]...

  Local repository context engine for AI coding agents.

Commands:
  setup-project  One-command setup: init, index, install skills, register MCP
  init           Initialise .repo-brain/ and create default config.json
  index          Scan the repository and generate context artifacts
  map            Print a readable repository summary from existing artifacts
  impact         Show what is affected if a file changes
  context        Suggest files, symbols, routes and tests relevant to a task
  serve          Start the MCP server on stdio
```

---

## Step 2 — Run setup-project

One command does everything:

```bash
cd /your/fastapi-project
repo-brain setup-project
```

```
╭──────────────────────────────────╮
│ repo-brain project setup         │
╰─ /your/fastapi-project ──────────╯
✓ Initialised .repo-brain/
✓ Indexed 41 Python files  (312 symbols · 18 routes · 9 test files)
✓ Installed 6 skills → .claude/commands
    /setup
    /impact-analysis
    /safe-refactor
    /bug-investigation
    /test-coverage
    /feature-implementation
✓ MCP server registered with Claude Code

Setup complete.
  Open Claude Code and type /setup to start your first session.
```

In under 10 seconds: full repo index, all skills installed as slash commands,
MCP server wired to Claude Code — before reading a single source file.

---

## Step 3 — Open Claude Code and run /setup

```
/setup
```

Claude checks the index, shows the repo map, and asks what you want to work on.
Because `setup-project` already indexed the repo, the index is fresh and this
takes under 5 seconds.

---

## Step 4 — Understand the task context

The ticket says: *"Add audit logging every time a document is uploaded."*

```bash
repo-brain context "audit logging document upload"
```

```
╭──────────────────────────── Task Context ─────────────────────────────╮
│ "audit logging document upload"                                       │
│ keywords: audit, logging, document, upload                            │
╰───────────────────────────────────────────────────────────────────────╯

Suggested files to read (4)
  app/services/document_service.py  ████ (4)
  app/routes/documents.py           ██ (2)
  app/models/document.py            █ (1)
  tests/test_document_service.py    █ (1)

Suggested symbols (6)
  class     DocumentService      app/services/document_service.py:12   score 4
  function  upload_document      app/services/document_service.py:34   score 3
  function  upload_document      app/routes/documents.py:28            score 2
  function  test_upload_document tests/test_document_service.py:15     score 2
  class     Document             app/models/document.py:5              score 1
  function  get_document         app/services/document_service.py:55   score 1

Suggested routes (2)
  POST  /documents/upload  → upload_document  (app/routes/documents.py)
  GET   /documents/{id}    → get_document     (app/routes/documents.py)

Suggested tests (2)
  tests/test_document_service.py
  tests/test_documents_routes.py

Saved to .repo-brain/last_context.json
```

You now know — without reading any code — that the change belongs in
`app/services/document_service.py`, specifically `upload_document`, and that
`tests/test_document_service.py` is where the new test should go.

---

## Step 5 — Check impact before touching anything

Before writing a single line, run impact on the file you are about to change:

```bash
repo-brain impact app/services/document_service.py
```

```
╭──────────────────────────── Impact Analysis ──────────────────────────╮
│ app/services/document_service.py                                      │
│ module: app.services.document_service                                 │
╰───────────────────────────────────────────────────────────────────────╯

Symbols defined in this file (5)
  class     DocumentService      line 12
  function  upload_document      line 34
  function  get_document         line 55
  function  delete_document      line 71
  function  list_documents       line 88

FastAPI routes defined in this file (0)

Imported by (3)
  app/routes/documents.py
  app/dependencies.py
  tests/test_document_service.py

Related tests (1)
  tests/test_document_service.py

Likely affected files (3)
  • app/dependencies.py
  • app/routes/documents.py
  • tests/test_document_service.py
```

You now know:
- Three files import this service — you must not break them
- One test file covers it — you must keep it passing
- The routes file calls this service — the route handler will be unaffected
  because you are adding logic inside the service, not changing its interface

---

## Step 6 — Implement the change

You open `app/services/document_service.py` and add audit logging inside
`upload_document`. The interface (function name, parameters, return type)
does not change — so the three importers are safe.

```python
# app/services/document_service.py

async def upload_document(file: UploadFile, user_id: int) -> Document:
    doc = await _save_file(file)
    await audit_log.write(user_id=user_id, action="document.upload", target=doc.id)  # new
    return doc
```

---

## Step 7 — Write the test

You open `tests/test_document_service.py` and add:

```python
async def test_upload_document_writes_audit_log(mock_audit_log):
    await upload_document(fake_file, user_id=42)
    mock_audit_log.write.assert_called_once_with(
        user_id=42, action="document.upload", target=ANY
    )
```

---

## Step 8 — Verify nothing is broken

```bash
python -m pytest tests/test_document_service.py tests/test_documents_routes.py -v
```

All pass. Re-index so artifacts reflect the new audit import:

```bash
repo-brain index
```

Run impact again to confirm the picture is still correct:

```bash
repo-brain impact app/services/document_service.py
```

The output looks the same — the interface did not change, no new callers appeared.
You are safe to commit.

---

## Step 9 — MCP and skills (already done via setup-project)

If you ran `repo-brain setup-project` in Step 2, MCP and skills are already
configured. Verify with:

```bash
claude mcp list
```

```
repo-brain  repo-brain serve --root /your/fastapi-project  ✓ connected
```

Now in any Claude Code session, the agent can call:

```
repo_brain_status()
repo_brain_task_context(task="add pagination to list endpoints")
repo_brain_impact(file_path="app/services/document_service.py")
repo_brain_search_symbol(name="DocumentService")
repo_brain_tests(file_path="app/services/document_service.py")
```

Without you typing a single command.

---

## Step 9 — Install skills as slash commands

```bash
mkdir -p .claude/commands
cp /path/to/repo-brain/skills/*.md .claude/commands/
```

This installs 6 skills as Claude Code slash commands:

| Command | When to use |
|---------|-------------|
| `/setup` | **Start of every session** — init, index, map, ask task, run context |
| `/impact-analysis` | Before touching any file |
| `/safe-refactor` | Renaming or moving code |
| `/bug-investigation` | Debugging a failure |
| `/test-coverage` | Finding and filling test gaps |
| `/feature-implementation` | Starting a new feature |

---

## Step 10 — The `/setup` experience

From now on, every Claude Code session on this project starts with one command:

```
/setup
```

Claude does the following automatically — no prompts needed:

```
Checking repo-brain status...

✓ .repo-brain/ found
✓ Index is fresh (scanned 8 minutes ago)

Repository overview:
  Python files   41  |  Routes  18
  Classes        28  |  Tests    9
  Functions     284  |  Modules  app, tests

What would you like to work on today?
```

You answer in plain English:

```
> Add rate limiting to the document upload endpoint
```

Claude immediately runs `repo_brain_task_context` and responds:

```
Start by reading:
  app/routes/documents.py          ████ score 4
  app/middleware/                  ██   score 2
  app/services/document_service.py █    score 1

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

You go from opening Claude Code to knowing exactly where to start — in under
30 seconds, without reading a single file manually.

If the index is stale (e.g. first session of the day after yesterday's work),
`/setup` re-indexes automatically before showing the map:

```
Index is 14 hours old — re-indexing now...

Indexed 43 Python files.  (+2 since last run)
  Symbols : 318  Routes : 19  Tests : 9

Repository overview: ...
```

---

## Other skills in action

Once `/setup` has oriented the session, reach for the right skill:

```
/feature-implementation "add pagination to list endpoints"
```

Claude follows the structured workflow:
1. Calls `repo_brain_status()` to understand repo shape
2. Calls `repo_brain_task_context(task=...)` to find relevant files
3. Reads existing patterns before writing anything
4. Plans: model → service → route → tests
5. Implements bottom-up, verifying at each layer

Or before a risky change:

```
/impact-analysis app/services/document_service.py
```

Claude runs the full impact workflow, reads all importers and tests,
and gives you a written list of what to touch before starting.

---

## Daily workflow

Once repo-brain and skills are set up, the full routine is:

```
Start of session
  └── /setup                        ← always first; inits, re-indexes if stale,
                                       shows map, asks task, runs context

Before any change
  └── /impact-analysis <file>       ← reads importers and tests before touching

Starting a new feature
  └── /feature-implementation "<task>"

Debugging
  └── /bug-investigation "<symptom>"

Checking test coverage
  └── /test-coverage <file>

Renaming or moving code
  └── /safe-refactor <file>

Before committing
  └── python -m pytest
  └── repo-brain index              ← keep artifacts fresh for the next session
```

---

## What changes for the AI agent

Without repo-brain, Claude Code in a new session:
1. Lists all files in the repo
2. Searches for keywords across files
3. Opens files one at a time to understand structure
4. Asks you clarifying questions about architecture
5. May still miss callers or related tests

With repo-brain + MCP:
1. Calls `repo_brain_status()` — instant project overview
2. Calls `repo_brain_task_context(task=...)` — ranked file list in milliseconds
3. Opens only the 2–3 most relevant files
4. Calls `repo_brain_impact(...)` before touching anything
5. Proceeds with confidence, never missing a caller or test

**Result:** fewer files opened, fewer clarifying questions, fewer broken
callers, more targeted tests — on every task.
