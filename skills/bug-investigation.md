# Skill: Bug Investigation

Use this skill when a bug is reported to rapidly locate which files,
routes, and tests are involved — before reading any source code.

---

## When to use

- A bug report arrives ("endpoint X returns 500", "function Y crashes")
- A test is failing and you don't know why
- Unexpected behaviour appears after a recent change
- You need to understand the blast radius of a known defect

---

## Prerequisites

- `repo-brain index` is up to date
- You have a bug description or failing test name

---

## Input

```
BUG: <one-line description of the bug or failing test>
Example: "POST /documents/upload returns 422 when file is missing"
Example: "test_upload_document fails with AttributeError"
```

---

## Steps

### 1. Extract the key terms from the bug description

Read the bug and identify:
- Route path (e.g. `/documents/upload`)
- Function or class name (e.g. `upload_document`, `DocumentService`)
- Module or file name (e.g. `document_service`, `upload`)

### 2. Get task context for the bug keywords

```
CLI: repo-brain context "<BUG keywords>"
MCP: repo_brain_task_context(task="<BUG keywords>")
```

This gives you a ranked list of:
- **Files likely involved** — read these first
- **Symbols likely involved** — functions and classes to inspect
- **Routes involved** — the API endpoints closest to the bug
- **Tests to run** — the specific tests to execute to reproduce

### 3. Search for the specific symbol mentioned in the bug

If the bug names a function or class:

```
MCP: repo_brain_search_symbol(name="<SymbolName>")
```

Note the file path and line number. That is where you start reading.

### 4. Run impact analysis on the most likely file

```
CLI: repo-brain impact <most-likely-file>
MCP: repo_brain_impact(file_path="<most-likely-file>")
```

Read:
- **Routes defined** — confirm the broken route is handled here
- **Imported by** — other files that might be passing bad data in
- **Related tests** — run these to reproduce the failure

### 5. Run the related tests

```bash
python -m pytest <test-file-from-step-4> -v
```

Reproduce the failure locally before reading any more code.
A bug you cannot reproduce is a bug you cannot safely fix.

### 6. Trace the call path

Starting from the route handler (from Step 4):
- Read the handler function
- Follow calls into service/utility files
- At each step, use `repo_brain_search_symbol` to find the next symbol
- Stop when you find the line that produces the wrong behaviour

### 7. Identify the fix scope

Before writing any code, answer:
- Which file contains the defect?
- Which other files (from "Imported by") might need updating?
- Which tests will verify the fix?
- Are there other routes or callers that share the same bug?

---

## Success criteria

- You can name the exact file and line where the bug originates
- You can reproduce the failure with a specific test or curl command
- You have a list of files to change and tests to add/update

---

## Safety rules

- Do not fix what you have not reproduced — you will fix the wrong thing
- Do not change more than the minimum needed to fix the bug
- Add a regression test that fails before your fix and passes after
- Re-run `repo-brain impact` on every file you change before committing

---

## After your fix

```bash
python -m pytest                   # all tests must pass
repo-brain index
repo-brain impact <fixed-file>    # confirm impact is as expected
```

Confirm the regression test you added now passes.
