from __future__ import annotations

import json
from pathlib import Path

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from repo_brain.config import brain_dir
from repo_brain.context import build_context, load_context_artifacts
from repo_brain.impact import analyse, load_impact_artifacts
from repo_brain.models import ImportInfo, RouteInfo, SymbolInfo, TestInfo

# ---------------------------------------------------------------------------
# Pure handler functions — each returns a plain dict/list, no MCP coupling.
# These are what tests exercise directly.
# ---------------------------------------------------------------------------

def handle_status(bd: Path) -> dict:
    p = bd / "repo_map.json"
    if not p.exists():
        return {"error": "No index found. Run `repo-brain index` first."}
    data = json.loads(p.read_text())
    routes_count = _count_json(bd / "routes.json")
    symbols = _load_json(bd / "symbols.json")
    tests_count = _count_json(bd / "tests.json")
    return {
        "project_name": data.get("project_name"),
        "python_file_count": data.get("python_file_count", 0),
        "top_level_modules": data.get("top_level_modules", []),
        "scan_timestamp": data.get("scan_timestamp"),
        "classes": sum(1 for s in symbols if s.get("symbol_type") == "class"),
        "functions": sum(1 for s in symbols if s.get("symbol_type") in ("function", "async_function")),
        "routes": routes_count,
        "test_files": tests_count,
    }


def handle_search_symbol(bd: Path, name: str, symbol_type: str | None = None) -> list[dict]:
    symbols = [SymbolInfo(**s) for s in _load_json(bd / "symbols.json")]
    query = name.lower()
    results = []
    for s in symbols:
        if query not in s.name.lower():
            continue
        if symbol_type and s.symbol_type != symbol_type:
            continue
        results.append({
            "name": s.name,
            "symbol_type": s.symbol_type,
            "file_path": s.file_path,
            "lineno": s.lineno,
            "end_lineno": s.end_lineno,
            "parent": s.parent,
        })
    return sorted(results, key=lambda x: x["name"])


def handle_related_files(bd: Path, file_path: str) -> dict:
    symbols, routes, imports, tests = _load_impact(bd)
    result = analyse(file_path, symbols, routes, imports, tests)
    return {
        "target_file": result.target_file,
        "imported_by": result.imported_by,
        "related_tests": result.related_tests,
        "likely_affected": result.likely_affected,
    }


def handle_impact(bd: Path, file_path: str) -> dict:
    symbols, routes, imports, tests = _load_impact(bd)
    result = analyse(file_path, symbols, routes, imports, tests)
    return result.model_dump()


def handle_tests(bd: Path, file_path: str | None = None) -> list[dict]:
    raw = _load_json(bd / "tests.json")
    all_tests = [{"file_path": t["file_path"], "test_functions": t["test_functions"], "test_classes": t["test_classes"]} for t in raw]
    if not file_path:
        return all_tests
    query = Path(file_path).stem.lower().removeprefix("test_").removesuffix("_test")
    return [
        t for t in all_tests
        if query in t["file_path"].lower()
        or any(query in fn.lower() for fn in t["test_functions"])
    ]


def handle_task_context(bd: Path, task: str) -> dict:
    symbols, routes, imports, tests = load_context_artifacts(bd)
    result = build_context(task, symbols, routes, imports, tests)
    return {
        "task": result.task,
        "keywords": result.keywords,
        "suggested_files": [{"path": f.path, "score": f.score} for f in result.suggested_files],
        "suggested_symbols": [
            {
                "name": ss.symbol.name,
                "symbol_type": ss.symbol.symbol_type,
                "file_path": ss.symbol.file_path,
                "lineno": ss.symbol.lineno,
                "score": ss.score,
            }
            for ss in result.suggested_symbols
        ],
        "suggested_routes": [r.model_dump() for r in result.suggested_routes],
        "suggested_tests": result.suggested_tests,
    }


# ---------------------------------------------------------------------------
# MCP server wiring
# ---------------------------------------------------------------------------

_TOOLS = [
    types.Tool(
        name="repo_brain_status",
        description="Return a summary of the indexed repository: file count, modules, classes, functions, routes, and test files.",
        inputSchema={"type": "object", "properties": {}},
    ),
    types.Tool(
        name="repo_brain_search_symbol",
        description="Search for classes, functions, or methods by name (substring match). Optionally filter by symbol_type.",
        inputSchema={
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Symbol name or substring to search for"},
                "symbol_type": {
                    "type": "string",
                    "description": "Optional filter: class, function, async_function, method, async_method",
                },
            },
            "required": ["name"],
        },
    ),
    types.Tool(
        name="repo_brain_related_files",
        description="Given a file path, return files that import it, related test files, and the full likely-affected list.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to the target file"},
            },
            "required": ["file_path"],
        },
    ),
    types.Tool(
        name="repo_brain_impact",
        description="Full impact analysis for a file: symbols defined, routes, importers, related tests, and likely-affected files.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Relative path to the target file"},
            },
            "required": ["file_path"],
        },
    ),
    types.Tool(
        name="repo_brain_tests",
        description="Return test files and their test functions. If file_path is given, filter to tests related to that file.",
        inputSchema={
            "type": "object",
            "properties": {
                "file_path": {"type": "string", "description": "Optional: filter tests related to this file"},
            },
        },
    ),
    types.Tool(
        name="repo_brain_task_context",
        description=(
            "Given a natural-language task description, return ranked suggestions: "
            "files to read, symbols to look at, routes involved, and tests to run."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Natural-language description of the task"},
            },
            "required": ["task"],
        },
    ),
]


def make_server(root: Path) -> Server:
    server = Server("repo-brain")
    bd = brain_dir(root)

    @server.list_tools()
    async def list_tools() -> list[types.Tool]:
        return _TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
        if not bd.exists():
            payload = {"error": "No .repo-brain/ found. Run `repo-brain init` and `repo-brain index` first."}
            return [types.TextContent(type="text", text=json.dumps(payload, indent=2))]

        try:
            result = _dispatch(name, arguments, bd)
        except Exception as exc:
            result = {"error": str(exc)}

        return [types.TextContent(type="text", text=json.dumps(result, indent=2))]

    return server


def _dispatch(name: str, arguments: dict, bd: Path) -> object:
    if name == "repo_brain_status":
        return handle_status(bd)
    if name == "repo_brain_search_symbol":
        return handle_search_symbol(bd, arguments["name"], arguments.get("symbol_type"))
    if name == "repo_brain_related_files":
        return handle_related_files(bd, arguments["file_path"])
    if name == "repo_brain_impact":
        return handle_impact(bd, arguments["file_path"])
    if name == "repo_brain_tests":
        return handle_tests(bd, arguments.get("file_path"))
    if name == "repo_brain_task_context":
        return handle_task_context(bd, arguments["task"])
    return {"error": f"Unknown tool: {name}"}


async def run_server(root: Path) -> None:
    server = make_server(root)
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _load_json(path: Path) -> list:
    return json.loads(path.read_text()) if path.exists() else []


def _count_json(path: Path) -> int:
    return len(_load_json(path))


def _load_impact(bd: Path):
    return load_impact_artifacts(bd)
