# repo-brain Skills

Workflow instruction files for AI coding agents.

Each skill is a structured Markdown document that tells an agent exactly what steps to follow — using repo-brain CLI commands or MCP tools — to complete a specific type of task safely and correctly.

---

## Available skills

| Skill | File | When to use |
|-------|------|-------------|
| **Setup** | `setup.md` | **Start of every session** — init, index, map, ask task |
| Impact Analysis | `impact-analysis.md` | Before touching any file — check what else breaks |
| Safe Refactor | `safe-refactor.md` | Renaming, moving, or restructuring existing code |
| Bug Investigation | `bug-investigation.md` | Locating a bug's reach across routes, tests, files |
| Test Coverage | `test-coverage.md` | Finding gaps and deciding what tests to write |
| Feature Implementation | `feature-implementation.md` | Starting a new feature with the right context |

> **Tip:** Always run `/setup` first. The other skills assume the index is fresh.

---

## How to install as Claude Code slash commands

Copy skills into your target repository's `.claude/commands/` directory.
Claude Code picks them up automatically as `/skill-name` commands.

```bash
# from inside your target repo
mkdir -p .claude/commands

# copy all skills
cp /path/to/repo-brain/skills/*.md .claude/commands/

# or copy individual skills
cp /path/to/repo-brain/skills/impact-analysis.md .claude/commands/
```

Then use them in Claude Code:

```
/impact-analysis src/services/users.py
/safe-refactor src/utils/helpers.py
/bug-investigation "login fails with 401 for valid tokens"
/test-coverage src/services/document_service.py
/feature-implementation "add pagination to list endpoints"
```

---

## How to use without Claude Code

Paste the skill content into any AI agent conversation and provide the
required input at the top. The agent will follow the steps.

---

## Prerequisites for all skills

1. repo-brain is installed: `pip install -e /path/to/repo-brain`
2. The target repo has been initialised: `repo-brain init`
3. The index is fresh: `repo-brain index`

If the index is stale (code changed since last `index` run), re-index first:

```bash
repo-brain index && repo-brain map
```

---

## How skills reference tools

Each step in a skill shows both the CLI command and the MCP tool name:

```
CLI:  repo-brain impact <file>
MCP:  repo_brain_impact(file_path="<file>")
```

Use whichever is available in your context. Results are identical.
