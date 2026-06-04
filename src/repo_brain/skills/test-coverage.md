# Skill: Test Coverage

Use this skill to find which files lack tests, understand what is already
covered, and decide what tests to write next.

---

## When to use

- Before merging a PR — check nothing important was left untested
- After implementing a feature — verify tests exist for every new symbol
- During a quality audit — find the most critical uncovered files
- When asked "what should I test next?"

---

## Prerequisites

- `repo-brain index` is up to date
- Tests live in `tests/` or follow `test_*.py` / `*_test.py` naming

---

## Input

```
SCOPE: <file, module, or "all">
Example: src/services/document_service.py
Example: src/services/
Example: all
```

---

## Steps

### 1. Get an overview of current test coverage

```
CLI: repo-brain map
MCP: repo_brain_status()
```

Note:
- Total Python files vs total test files
- If test file count is significantly lower than source file count,
  coverage is likely thin

### 2. List all known test files and their functions

```
MCP: repo_brain_tests()
```

Read the output. Build a mental map of what is currently tested.

### 3. Find tests related to your scope

If working on a specific file:

```
CLI: repo-brain impact <SCOPE-file>
MCP: repo_brain_impact(file_path="<SCOPE-file>")
```

Look at **Related tests**. If this list is empty, the file has no test coverage.

If working on a module or "all":

```
MCP: repo_brain_tests(file_path="<module-name>")
```

### 4. Identify symbols with no test coverage

List all symbols in your scope file:

```
MCP: repo_brain_search_symbol(name="", symbol_type="function")
MCP: repo_brain_search_symbol(name="", symbol_type="class")
```

Filter to those in your scope file. For each symbol, check whether a
test function exists that covers it by searching the test files from Step 2.

Symbols that have no matching test function are your coverage gaps.

### 5. Prioritise what to test

Rank uncovered symbols by risk:

| Priority | Signal |
|----------|--------|
| High | Symbol is called by a FastAPI route (visible in `routes.json`) |
| High | Symbol is imported by many files (wide impact radius) |
| Medium | Symbol contains business logic (not just data access) |
| Low | Private helper function (`_` prefix) or trivial getter/setter |

Focus on High first.

### 6. Write the missing tests

For each High-priority uncovered symbol:

1. Create or open the corresponding test file (`tests/test_<module>.py`)
2. Write at least:
   - One happy-path test
   - One edge-case or error test
3. Name tests as `test_<function_name>_<scenario>` for clarity

### 7. Verify the new tests pass

```bash
python -m pytest tests/test_<module>.py -v
```

All new tests must pass before you stop.

### 8. Re-index and confirm coverage improved

```bash
repo-brain index
repo-brain map
```

Confirm test file count increased (if you added a new test file).
Re-run `repo-brain impact <SCOPE-file>` and confirm **Related tests**
now shows your new test file.

---

## Success criteria

- Every FastAPI route in scope has at least one test
- Every public function (no `_` prefix) in scope has at least one test
- `repo-brain impact <scope-file>` shows non-empty **Related tests**
- `python -m pytest` passes with a higher test count than before

---

## Safety rules

- Do not write tests that only assert `True` or mock everything — they prove nothing
- Do not mark a file as "covered" based only on the filename match;
  verify the test actually imports and calls the functions
- Do not delete existing tests to make coverage numbers look better

---

## After your tests

```bash
python -m pytest
repo-brain index && repo-brain map
```

Commit your new tests in their own commit, separate from any code changes.
