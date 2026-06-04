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
cd /your/fastapi-project

# create a virtualenv if you don't have one
python3 -m venv .venv
source .venv/bin/activate

# install repo-brain
pip install -e /path/to/repo-brain
```

Verify it works:

```bash
repo-brain --help
```

```
Usage: repo-brain [OPTIONS] COMMAND [ARGS]...

  Local repository context engine for AI coding agents.

Commands:
  init     Initialise .repo-brain/ and create default config.json
  index    Scan the repository and generate context artifacts
  map      Print a readable repository summary from existing artifacts
  impact   Show what is affected if a file changes
  context  Suggest files, symbols, routes and tests relevant to a task
  serve    Start the MCP server on stdio
```

---

## Step 2 — Initialise and index your project

```bash
repo-brain init
```

```
Created /your/fastapi-project/.repo-brain
Config written to .repo-brain/config.json
```

```bash
repo-brain index
```

```
Indexed 41 Python files.
  Symbols : 312
  Imports : 287
  Routes  : 18
  Tests   : 9 test file(s)

Artifacts written to /your/fastapi-project/.repo-brain
```

```bash
repo-brain map
```

```
              Repository Map
  Project        my-fastapi-project
  Python files   41
  Classes        28
  Functions      284
  FastAPI routes 18
  Test files     9
  Scanned at     2026-06-04T10:30:00+00:00

Top-level modules:
  • app
  • tests
```

In under 10 seconds you have a full picture of the codebase — before reading
a single source file.

---

## Step 3 — Understand the task context

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

## Step 4 — Check impact before touching anything

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

## Step 5 — Implement the change

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

## Step 6 — Write the test

You open `tests/test_document_service.py` and add:

```python
async def test_upload_document_writes_audit_log(mock_audit_log):
    await upload_document(fake_file, user_id=42)
    mock_audit_log.write.assert_called_once_with(
        user_id=42, action="document.upload", target=ANY
    )
```

---

## Step 7 — Verify nothing is broken

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

## Step 8 — Connect to Claude Code via MCP

Do this once per project. It lets Claude Code call repo-brain tools directly
in every future conversation — no manual commands needed.

```bash
claude mcp add repo-brain -- repo-brain serve --root /your/fastapi-project
```

Verify it registered:

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

Now at the start of any task, you type:

```
/feature-implementation "add pagination to list endpoints"
```

Claude follows the structured workflow automatically:
1. Calls `repo_brain_status()` to understand the repo shape
2. Calls `repo_brain_task_context(task=...)` to find relevant files
3. Reads the suggested files to understand existing patterns
4. Plans the change before writing any code
5. Implements bottom-up: model → service → route → tests

Or before a risky change:

```
/impact-analysis app/services/document_service.py
```

Claude runs the full impact workflow, reads all importers, reads all related
tests, and gives you a written list of what to touch before starting.

---

## Daily workflow

Once repo-brain is set up, the routine is:

```
Morning / start of task
  └── repo-brain index          (re-index if code changed since yesterday)

Before any change
  └── repo-brain impact <file>  (or /impact-analysis in Claude Code)

Starting a new feature
  └── repo-brain context "<task>"  (or /feature-implementation)

Debugging
  └── repo-brain context "<bug keywords>"  (or /bug-investigation)

Before committing
  └── python -m pytest
  └── repo-brain index          (keep artifacts fresh for the next task)
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
