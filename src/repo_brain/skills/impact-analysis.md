# Skill: Impact Analysis

Run this skill **before making any change to a file** to understand what else
in the codebase will be affected.

---

## When to use

- Before editing, renaming, or deleting any Python file
- Before changing a function signature or class interface
- Before removing a route or changing its path
- When asked "what does this file touch?"

---

## Prerequisites

- `repo-brain index` has been run and is up to date
- The target file exists in the repository

---

## Input

```
TARGET: <relative path to the file you are about to change>
Example: src/services/document_service.py
```

---

## Steps

### 1. Run impact analysis on the target file

```
CLI: repo-brain impact <TARGET>
MCP: repo_brain_impact(file_path="<TARGET>")
```

Read the full output before proceeding. Note:
- **Symbols defined** — classes and functions you are changing
- **Routes defined** — any API endpoints in this file
- **Imported by** — files that will break if the interface changes
- **Related tests** — tests that must pass after your change
- **Likely affected** — the complete list of files needing attention

### 2. Check the repository status

```
CLI: repo-brain map
MCP: repo_brain_status()
```

Confirm the index is recent (check `Scanned at` timestamp).
If the index is stale, stop and run `repo-brain index` first.

### 3. Read every file in "Imported by"

Open each file listed under **Imported by** and understand:
- How it uses the target file's symbols
- Whether your change will break that usage
- Whether it needs to be updated in the same PR

### 4. Read every file in "Related tests"

Open each test file and understand:
- What behaviours are currently tested
- Which tests will break if you change the interface
- Which tests need to be updated or added

### 5. Search for additional usages of key symbols

For each class or function you are changing:

```
CLI: (use grep or your editor)
MCP: repo_brain_search_symbol(name="<SymbolName>")
```

Confirm the MCP result matches the "Imported by" list.
If you find extra usages not in the impact output, note them.

### 6. Plan your change

Before writing any code, list:
- [ ] Files to modify (from "Imported by" + "Related tests")
- [ ] Tests to update
- [ ] Tests to add (if interface changes)
- [ ] Routes to update (if path or handler signature changes)

---

## Success criteria

- You can name every file that imports the target
- You can name every test that covers the target
- You have a written list of files to touch before starting

---

## Safety rules

- Do not change a public interface (function signature, class name, route path)
  without first reading every file in "Imported by"
- Do not merge a change that breaks a test listed in "Related tests"
- If "Likely affected" has more than 5 files, consider breaking the change
  into smaller steps

---

## After your change

Re-run the full validation:

```bash
repo-brain index
repo-brain impact <TARGET>
python -m pytest
```

Confirm that test count has not dropped and all previously affected files
were updated.
