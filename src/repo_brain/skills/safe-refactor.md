# Skill: Safe Refactor

Use this skill when renaming, moving, splitting, or restructuring existing
code. It ensures every caller and test is updated before the change is committed.

---

## When to use

- Renaming a class, function, or module
- Moving a file to a different directory or package
- Splitting one file into multiple files
- Changing a function signature (adding/removing/renaming parameters)
- Changing a route path or HTTP method

---

## Prerequisites

- `repo-brain index` is up to date
- All existing tests pass before you start: `python -m pytest`
- You have a clear description of what is being renamed/moved

---

## Input

```
TARGET:  <relative path to the file being refactored>
CHANGE:  <one-line description, e.g. "rename UserService to AccountService">
```

---

## Steps

### 1. Snapshot the current state

```
CLI: repo-brain impact <TARGET>
MCP: repo_brain_impact(file_path="<TARGET>")
```

Save the output. This is your checklist of everything that must still work
after the refactor.

```
CLI: repo-brain map
MCP: repo_brain_status()
```

Note the current test count. It must not decrease when you are done.

### 2. Find every usage of the symbol being changed

```
MCP: repo_brain_search_symbol(name="<OldName>")
```

Or via grep:
```bash
grep -r "OldName" --include="*.py" .
```

List every file and line number. This is your update list.

### 3. Check all related tests

```
MCP: repo_brain_tests(file_path="<TARGET>")
```

Open each test file. Understand which behaviours are tested so you can
confirm they still pass after renaming.

### 4. Make the change in the target file first

- Rename the class/function/file
- Update any internal references within the same file
- Do not touch callers yet

### 5. Update every caller

Work through the list from Step 2 one file at a time:
- Replace the old name with the new name
- Update import statements if the module path changed
- Do not skip any file — a missed caller will cause a runtime error

### 6. Update every test

Work through the test files from Step 3:
- Replace the old name in imports and assertions
- Rename test functions if they reference the old name in their name
- Add a test for any new behaviour introduced by the refactor

### 7. Run the full test suite

```bash
python -m pytest
```

All tests must pass. If any fail, fix them before proceeding.

### 8. Re-index and verify

```bash
repo-brain index
repo-brain impact <TARGET>   # or the new path if file was moved/renamed
```

Confirm:
- "Imported by" reflects the updated callers
- "Related tests" still shows test coverage
- No old symbol name appears in the new impact output

---

## Success criteria

- `python -m pytest` passes with the same or higher test count
- `repo-brain search_symbol <OldName>` returns zero results
- `repo-brain impact <NewTarget>` shows correct importers and tests

---

## Safety rules

- Never rename and refactor logic in the same commit — rename first, then refactor
- Never skip a file in the caller list — missing one causes a silent runtime failure
- Do not reduce test coverage — if you move code, move its tests too
- If more than 10 files need updating, consider a phased approach:
  introduce the new name alongside the old, migrate callers, then remove the old name

---

## After your change

```bash
repo-brain index && repo-brain map
python -m pytest
```

Confirm test count is unchanged or higher. Review `repo-brain map` to
ensure module structure looks correct.
