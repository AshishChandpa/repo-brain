# Skill: Feature Implementation

Use this skill when starting a new feature to identify the right files
to change, understand existing patterns to follow, and plan tests before
writing any code.

---

## When to use

- Starting a new feature from a ticket or task description
- Adding a new API endpoint to an existing FastAPI app
- Extending an existing service with new behaviour
- When asked "where do I add X?"

---

## Prerequisites

- `repo-brain index` is up to date
- You have a clear feature description (one sentence minimum)

---

## Input

```
FEATURE: <one-line description of what you are building>
Example: "add pagination to the document list endpoint"
Example: "add audit logging when a document is uploaded"
Example: "add a user profile update endpoint"
```

---

## Steps

### 1. Understand what already exists

```
CLI: repo-brain map
MCP: repo_brain_status()
```

Read:
- Top-level modules — understand the package structure
- Route count — understand how many endpoints already exist
- Test count — understand the testing baseline you must maintain

### 2. Get context for your feature

```
CLI: repo-brain context "<FEATURE>"
MCP: repo_brain_task_context(task="<FEATURE>")
```

Read the full output carefully:

- **Suggested files** — these are where similar code already lives;
  follow the patterns in these files
- **Suggested symbols** — classes and functions you will likely call or extend
- **Suggested routes** — existing routes nearest to what you are adding
- **Suggested tests** — test files where your new tests should live

### 3. Read the most relevant existing files

Open the top 3 files from **Suggested files**. For each one:
- Understand the pattern (how routes are defined, how services are structured)
- Note the import style
- Note how errors are handled
- Note how dependencies are injected

Do not write any code yet. You are learning the shape of the codebase.

### 4. Understand the existing route pattern

```
MCP: repo_brain_search_symbol(name="<nearest existing route handler>")
```

Open that handler. Read:
- How it validates input
- How it calls the service layer
- What it returns on success and error

Your new route should follow the same pattern exactly.

### 5. Run impact on the file you will change most

```
CLI: repo-brain impact <most-relevant-file>
MCP: repo_brain_impact(file_path="<most-relevant-file>")
```

Understand:
- Who already imports this file (you must not break them)
- Which tests already exist (you must not break them)
- Which routes it owns (you are adding to this list)

### 6. Plan before coding

Write a short plan (in your response, not in a file):

```
New route:    METHOD /path
Handler:      function_name (in file: <path>)
Service call: ServiceClass.method_name (in file: <path>)
New model:    (if needed) <ClassName> (in file: <path>)
Tests to add: test_<feature>_success, test_<feature>_invalid_input
Test file:    tests/test_<module>.py
Files to touch:
  - <file1> (add route)
  - <file2> (add service method)
  - <file3> (add tests)
```

Do not start coding until this plan is written and makes sense.

### 7. Implement bottom-up

Always implement in this order — it prevents calling code that does not exist yet:

1. **Model / schema** (if a new Pydantic model is needed)
2. **Service method** (the business logic)
3. **Route handler** (calls the service)
4. **Tests** (cover success, validation error, edge case)

### 8. Verify at each layer

After each layer:

```bash
python -m pytest -x    # stop on first failure
```

Fix failures immediately. Do not move to the next layer with a failing test.

### 9. Final validation

```bash
repo-brain index
repo-brain map
repo-brain context "<FEATURE>"   # confirm your new files appear in suggestions
python -m pytest
```

Confirm:
- Your new route appears in `routes.json` (`repo-brain map` shows updated route count)
- Your new test file appears in `tests.json`
- `repo-brain context "<FEATURE>"` surfaces your new files near the top
- All existing tests still pass

---

## Success criteria

- The new route responds correctly to a valid request
- The new route returns a clear error for invalid input
- At least one happy-path and one error-path test exist
- `python -m pytest` passes with a higher test count than before
- `repo-brain map` shows the new route

---

## Safety rules

- Do not modify existing routes or service methods unless the feature requires it;
  if it does, run the **Safe Refactor** skill first
- Do not skip writing the service layer — put business logic there, not in the route handler
- Do not merge without tests — a route with no test is a route that can silently regress
- Do not introduce a new dependency (pip package) without discussing it first

---

## After implementation

```bash
repo-brain index && repo-brain map
python -m pytest
```

Commit in this order:
1. Model/schema changes (if any)
2. Service layer changes
3. Route changes
4. Tests (in a separate commit or together with the code, never before)
