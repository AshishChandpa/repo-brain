from __future__ import annotations

import importlib.resources as pkg_resources
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from repo_brain.config import Config, brain_dir, load_config, save_config
from repo_brain.context import build_context, get_diff_files, load_context_artifacts
from repo_brain.export import export_context
from repo_brain.gaps import find_gaps, load_gaps_artifacts
from repo_brain.impact import analyse, load_impact_artifacts
from repo_brain.mcp_server import run_server
from repo_brain.models import RepoMap
from repo_brain.scanner import file_counts_by_language, scan, scan_incremental, top_level_modules
from repo_brain.writers.json_writer import write_artifacts, write_hashes
from repo_brain.writers.markdown_writer import write_markdown

app = typer.Typer(
    name="repo-brain",
    help="Local repository context engine for AI coding agents.",
    add_completion=False,
)
console = Console()


@app.command()
def init(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Initialise .repo-brain/ and create default config.json."""
    bd = brain_dir(root)
    if bd.exists():
        console.print(f"[yellow].repo-brain/ already exists at {bd.resolve()}[/yellow]")
    else:
        bd.mkdir(parents=True)
        console.print(f"[green]Created {bd.resolve()}[/green]")

    config = Config()
    save_config(config, root)
    console.print(f"[green]Config written to {bd / 'config.json'}[/green]")


@app.command()
def index(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
    force: bool = typer.Option(False, "--force", help="Force full re-scan (ignore file hashes)"),
) -> None:
    """Scan the repository and generate context artifacts.

    Uses incremental indexing by default — only re-parses changed files.
    Use --force for a full re-scan.
    """
    bd = brain_dir(root)
    if not bd.exists():
        console.print("[red]Run `repo-brain init` first.[/red]")
        raise typer.Exit(1)

    config = load_config(root)

    if force:
        with console.status("[bold green]Scanning repository (full)…[/bold green]"):
            result = scan(root, config)
        new_hashes = None
    else:
        with console.status("[bold green]Scanning repository (incremental)…[/bold green]"):
            result, new_hashes = scan_incremental(root, config, bd)

    modules = top_level_modules(result.files, root)
    timestamp = datetime.now(timezone.utc).isoformat()
    lang_counts = file_counts_by_language(result.files)

    repo_map = RepoMap(
        project_name=config.project_name,
        scan_timestamp=timestamp,
        python_file_count=lang_counts.get("python", 0),
        file_counts=lang_counts,
        top_level_modules=modules,
        artifact_paths={
            "repo_map": str(bd / "repo_map.json"),
            "symbols": str(bd / "symbols.json"),
            "imports": str(bd / "imports.json"),
            "routes": str(bd / "routes.json"),
            "tests": str(bd / "tests.json"),
            "call_graph": str(bd / "call_graph.json"),
            "route_links": str(bd / "route_links.json"),
            "markdown": str(bd / "REPO_MAP.md"),
        },
    )

    write_artifacts(bd, result, repo_map)
    write_markdown(bd, result, repo_map)
    if new_hashes is not None:
        write_hashes(bd, new_hashes)

    total = len(result.files)
    lang_summary = "  ".join(f"{lang}: {count}" for lang, count in sorted(lang_counts.items()))
    console.print(f"[green]Indexed {total} file(s).[/green]  [dim]{lang_summary}[/dim]")
    console.print(f"  Symbols    : {len(result.symbols)}")
    console.print(f"  Imports    : {len(result.imports)}")
    console.print(f"  Routes     : {len(result.routes)}")
    console.print(f"  Tests      : {len(result.tests)} test file(s)")
    console.print(f"  Call edges : {len(result.calls)}")
    console.print(f"  Route links: {len(result.route_links)}")
    mode = "[dim](full)[/dim]" if force else "[dim](incremental)[/dim]"
    console.print(f"\nArtifacts written to [bold]{bd.resolve()}[/bold]  {mode}")


@app.command(name="map")
def repo_map(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Print a readable repository summary from existing artifacts."""
    bd = brain_dir(root)
    map_file = bd / "repo_map.json"

    if not map_file.exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    data = json.loads(map_file.read_text())

    routes_file = bd / "routes.json"
    routes_count = len(json.loads(routes_file.read_text())) if routes_file.exists() else 0

    symbols_file = bd / "symbols.json"
    symbols = json.loads(symbols_file.read_text()) if symbols_file.exists() else []
    classes = sum(1 for s in symbols if s["symbol_type"] == "class")
    functions = sum(1 for s in symbols if s["symbol_type"] in ("function", "async_function"))

    tests_file = bd / "tests.json"
    test_file_count = len(json.loads(tests_file.read_text())) if tests_file.exists() else 0

    calls_file = bd / "call_graph.json"
    call_count = len(json.loads(calls_file.read_text())) if calls_file.exists() else 0

    route_links_file = bd / "route_links.json"
    route_links_count = len(json.loads(route_links_file.read_text())) if route_links_file.exists() else 0

    table = Table(title="Repository Map", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    project = data.get("project_name") or "[dim]unnamed[/dim]"
    lang_counts = data.get("file_counts", {})
    total_files = sum(lang_counts.values()) if lang_counts else data.get("python_file_count", 0)
    lang_str = "  ".join(f"{l}: {c}" for l, c in sorted(lang_counts.items())) if lang_counts else ""

    table.add_row("Project", project)
    table.add_row("Total files", f"{total_files}  [dim]{lang_str}[/dim]" if lang_str else str(total_files))
    table.add_row("Classes", str(classes))
    table.add_row("Functions", str(functions))
    table.add_row("Routes", str(routes_count))
    table.add_row("Test files", str(test_file_count))
    table.add_row("Call graph edges", str(call_count))
    table.add_row("Route links", str(route_links_count))
    table.add_row("Scanned at", data.get("scan_timestamp", "—"))

    console.print(table)

    modules = data.get("top_level_modules", [])
    if modules:
        console.print("\n[bold]Top-level modules:[/bold]")
        for m in modules:
            console.print(f"  • {m}")

    md_path = bd / "REPO_MAP.md"
    if md_path.exists():
        console.print(f"\n[dim]REPO_MAP.md → {md_path.resolve()}[/dim]")


@app.command()
def impact(
    file: Path = typer.Argument(..., help="Target file to analyse (relative to repo root)"),
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Show what is affected if a file changes (import graph + call graph)."""
    bd = brain_dir(root)

    if not (bd / "symbols.json").exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    try:
        target = str(file.relative_to(root))
    except ValueError:
        target = str(file)

    symbols, routes, imports, tests, calls = load_impact_artifacts(bd)
    result = analyse(target, symbols, routes, imports, tests, calls)

    console.print()
    console.print(Panel(
        f"[bold]{result.target_file}[/bold]\n[dim]module: {result.module_path or '—'}[/dim]",
        title="[bold cyan]Impact Analysis[/bold cyan]",
        expand=False,
    ))

    _section("Symbols defined in this file", len(result.symbols))
    for s in result.symbols:
        kind = f"[dim]{s.symbol_type}[/dim]"
        parent = f"  [dim](in {s.parent})[/dim]" if s.parent else ""
        console.print(f"  {kind}  [bold]{s.name}[/bold]{parent}  [dim]line {s.lineno}[/dim]")

    _section("Routes defined in this file", len(result.routes))
    for r in result.routes:
        console.print(f"  [green]{r.method.upper()}[/green]  {r.path}  [dim]→ {r.function_name}[/dim]")

    _section("Imported by", len(result.imported_by))
    for f in result.imported_by:
        console.print(f"  [yellow]{f}[/yellow]")

    _section("Called by (call graph)", len(result.callers))
    for f in result.callers:
        console.print(f"  [yellow]{f}[/yellow]")

    _section("Related tests", len(result.related_tests))
    for f in result.related_tests:
        console.print(f"  [magenta]{f}[/magenta]")

    _section("Likely affected files", len(result.likely_affected))
    for f in result.likely_affected:
        console.print(f"  • {f}")

    if not result.likely_affected:
        console.print("  [dim]No other files appear to depend on this file.[/dim]")

    out = bd / "last_impact.json"
    out.write_text(json.dumps(result.model_dump(), indent=2), encoding="utf-8")
    console.print(f"\n[dim]Saved to {out.resolve()}[/dim]")


@app.command()
def context(
    task: str = typer.Argument(..., help="Natural-language task description"),
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
    since: Optional[str] = typer.Option(None, "--since", help="Boost files changed since this git ref (e.g. HEAD~3, HEAD)"),
) -> None:
    """Suggest files, symbols, routes and tests relevant to a task.

    Use --since HEAD~3 to boost recently changed files higher in results.
    """
    bd = brain_dir(root)

    if not (bd / "symbols.json").exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    diff_files: set[str] = set()
    if since:
        diff_files = get_diff_files(root, since)
        if diff_files:
            console.print(f"[dim]Git diff ({since}): {len(diff_files)} changed file(s) will be boosted[/dim]")

    symbols, routes, imports, tests = load_context_artifacts(bd)
    result = build_context(task, symbols, routes, imports, tests, diff_files=diff_files)

    console.print()
    console.print(Panel(
        f'[bold]"{result.task}"[/bold]\n[dim]keywords: {", ".join(result.keywords) or "none matched"}[/dim]',
        title="[bold cyan]Task Context[/bold cyan]",
        expand=False,
    ))

    if not result.keywords:
        console.print("[yellow]No meaningful keywords found. Try a more specific task description.[/yellow]")
        raise typer.Exit(0)

    _section("Suggested files to read", len(result.suggested_files))
    for sf in result.suggested_files:
        diff_tag = " [bold cyan][diff][/bold cyan]" if since and sf.path in diff_files else ""
        bar = "█" * sf.score
        console.print(f"  [yellow]{sf.path}[/yellow]  [dim]{bar} ({sf.score})[/dim]{diff_tag}")

    _section("Suggested symbols", len(result.suggested_symbols))
    for ss in result.suggested_symbols:
        s = ss.symbol
        kind = f"[dim]{s.symbol_type}[/dim]"
        parent = f"  [dim](in {s.parent})[/dim]" if s.parent else ""
        console.print(
            f"  {kind}  [bold]{s.name}[/bold]{parent}"
            f"  [dim]{s.file_path}:{s.lineno}[/dim]"
            f"  [dim]score {ss.score}[/dim]"
        )

    _section("Suggested routes", len(result.suggested_routes))
    for r in result.suggested_routes:
        console.print(
            f"  [green]{r.method.upper()}[/green]  {r.path}"
            f"  [dim]→ {r.function_name}  ({r.file_path})[/dim]"
        )

    _section("Suggested tests", len(result.suggested_tests))
    for t in result.suggested_tests:
        console.print(f"  [magenta]{t}[/magenta]")

    if not any([
        result.suggested_files,
        result.suggested_symbols,
        result.suggested_routes,
        result.suggested_tests,
    ]):
        console.print("\n[dim]No matches found. Try different keywords or run `repo-brain index` first.[/dim]")

    out = bd / "last_context.json"
    out.write_text(json.dumps(result.model_dump(), indent=2), encoding="utf-8")
    console.print(f"\n[dim]Saved to {out.resolve()}[/dim]")


@app.command()
def gaps(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
    file: Optional[Path] = typer.Option(None, "--file", help="Filter to symbols in this file"),
) -> None:
    """Show symbols (classes, functions) with no apparent test coverage."""
    bd = brain_dir(root)

    if not (bd / "symbols.json").exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    file_filter = str(file) if file else None
    symbols, tests = load_gaps_artifacts(bd)
    gap_list = find_gaps(symbols, tests, file_filter=file_filter)

    console.print()
    console.print(Panel(
        f"[bold]{len(gap_list)} untested symbol(s)[/bold]"
        + (f"\n[dim]filtered to: {file_filter}[/dim]" if file_filter else ""),
        title="[bold cyan]Test Gaps[/bold cyan]",
        expand=False,
    ))

    if not gap_list:
        console.print("[green]No gaps found — all public symbols appear to have test coverage.[/green]")
        raise typer.Exit(0)

    current_file = ""
    for g in gap_list:
        if g.file_path != current_file:
            current_file = g.file_path
            console.print(f"\n[bold yellow]{current_file}[/bold yellow]")
        kind = f"[dim]{g.symbol_type}[/dim]"
        console.print(f"  {kind}  [bold]{g.symbol_name}[/bold]  [dim]line {g.lineno}[/dim]")

    out = bd / "gaps.json"
    out.write_text(json.dumps([g.model_dump() for g in gap_list], indent=2), encoding="utf-8")
    console.print(f"\n[dim]Saved to {out.resolve()}[/dim]")


@app.command(name="export")
def export_cmd(
    task: str = typer.Argument(..., help="Natural-language task description"),
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
    out: Optional[Path] = typer.Option(None, "--out", help="Output file (default: .repo-brain/last_export.md)"),
) -> None:
    """Export relevant code snippets for a task as a single Markdown file.

    The output is paste-ready for any AI context window.
    """
    bd = brain_dir(root)

    if not (bd / "symbols.json").exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    with console.status("[bold green]Exporting context snippets…[/bold green]"):
        markdown = export_context(task, bd, root)

    output_path = out or (bd / "last_export.md")
    output_path.write_text(markdown, encoding="utf-8")

    token_estimate = len(markdown) // 4
    console.print(f"[green]Exported[/green] ~{token_estimate:,} tokens → [bold]{output_path.resolve()}[/bold]")
    console.print("[dim]Paste the file contents into your AI context window.[/dim]")


@app.command()
def watch(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Watch the repository for file changes and auto re-index.

    Keeps .repo-brain/ artifacts fresh while you code. Press Ctrl+C to stop.
    """
    bd = brain_dir(root)
    if not bd.exists():
        console.print("[red]No .repo-brain/ found. Run `repo-brain init` and `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    from repo_brain.watch import watch as _watch
    _watch(root)


@app.command(name="setup-project")
def setup_project(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
    commands_dir: Path = typer.Option(
        Path(".claude/commands"), "--commands-dir", help="Claude Code commands directory"
    ),
    skip_skills: bool = typer.Option(False, "--skip-skills", help="Skip installing skills"),
    skip_mcp: bool = typer.Option(False, "--skip-mcp", help="Skip registering MCP server"),
) -> None:
    """One-command setup: init, index, install skills, register MCP.

    Run this once per project to get a teammate fully set up:

        repo-brain setup-project

    Then type /setup in Claude Code to start any session.
    """
    console.print()
    console.print(Panel(
        "[bold]repo-brain[/bold] project setup",
        subtitle=str(root.resolve()),
        expand=False,
    ))

    # ── 1. init ─────────────────────────────────────────────────────────────
    bd = brain_dir(root)
    if bd.exists():
        console.print("[dim]✓ .repo-brain/ already exists — skipping init[/dim]")
    else:
        bd.mkdir(parents=True)
        config = Config()
        save_config(config, root)
        console.print("[green]✓ Initialised .repo-brain/[/green]")

    # ── 2. index (incremental) ────────────────────────────────────────────────
    config = load_config(root)
    with console.status("[bold green]Indexing repository…[/bold green]"):
        result, new_hashes = scan_incremental(root, config, bd)

    modules = top_level_modules(result.files, root)
    timestamp = datetime.now(timezone.utc).isoformat()
    lang_counts = file_counts_by_language(result.files)
    repo_map = RepoMap(
        project_name=config.project_name,
        scan_timestamp=timestamp,
        python_file_count=lang_counts.get("python", 0),
        file_counts=lang_counts,
        top_level_modules=modules,
        artifact_paths={
            "repo_map": str(bd / "repo_map.json"),
            "symbols": str(bd / "symbols.json"),
            "imports": str(bd / "imports.json"),
            "routes": str(bd / "routes.json"),
            "tests": str(bd / "tests.json"),
            "call_graph": str(bd / "call_graph.json"),
            "route_links": str(bd / "route_links.json"),
            "markdown": str(bd / "REPO_MAP.md"),
        },
    )
    write_artifacts(bd, result, repo_map)
    write_hashes(bd, new_hashes)
    write_markdown(bd, result, repo_map)
    console.print(
        f"[green]✓ Indexed {len(result.files)} file(s)[/green]"
        f"  [dim]({len(result.symbols)} symbols · {len(result.routes)} routes · "
        f"{len(result.tests)} test files · {len(result.calls)} call edges)[/dim]"
    )

    # ── 3. install skills ────────────────────────────────────────────────────
    if skip_skills:
        console.print("[dim]  Skills install skipped (--skip-skills)[/dim]")
    else:
        installed, skipped = _install_skills(root / commands_dir)
        if installed:
            console.print(f"[green]✓ Installed {len(installed)} skills → {commands_dir}[/green]")
            for name in installed:
                console.print(f"  [dim]  /{Path(name).stem}[/dim]")
        if skipped:
            console.print(f"[dim]  {len(skipped)} skill(s) already up to date[/dim]")

    # ── 4. register MCP ──────────────────────────────────────────────────────
    if skip_mcp:
        console.print("[dim]  MCP registration skipped (--skip-mcp)[/dim]")
    else:
        _register_mcp(root)

    # ── summary ──────────────────────────────────────────────────────────────
    console.print()
    console.print("[bold green]Setup complete.[/bold green]")
    console.print("  Open Claude Code and type [bold]/setup[/bold] to start your first session.")
    console.print("  Tip: run [bold]repo-brain watch[/bold] in a background terminal to keep the index live.")


def _install_skills(commands_dir: Path) -> tuple[list[str], list[str]]:
    commands_dir.mkdir(parents=True, exist_ok=True)
    skills_pkg = pkg_resources.files("repo_brain") / "skills"

    installed: list[str] = []
    skipped: list[str] = []

    for resource in skills_pkg.iterdir():
        name = resource.name
        if not name.endswith(".md") or name == "README.md":
            continue
        dest = commands_dir / name
        content = resource.read_text(encoding="utf-8")
        if dest.exists() and dest.read_text(encoding="utf-8") == content:
            skipped.append(name)
        else:
            dest.write_text(content, encoding="utf-8")
            installed.append(name)

    return installed, skipped


def _register_mcp(root: Path) -> None:
    claude = shutil.which("claude")
    if not claude:
        console.print(
            "[yellow]  Claude Code CLI not found — skipping MCP registration.[/yellow]\n"
            "  Run manually once claude is installed:\n"
            f"  [dim]claude mcp add repo-brain -- repo-brain serve --root {root.resolve()}[/dim]"
        )
        return

    cmd = [
        claude, "mcp", "add", "repo-brain",
        "--", "repo-brain", "serve", "--root", str(root.resolve()),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        console.print("[green]✓ MCP server registered with Claude Code[/green]")
    else:
        stderr = result.stderr.strip()
        if "already" in stderr.lower() or "exists" in stderr.lower():
            console.print("[dim]✓ MCP server already registered[/dim]")
        else:
            console.print(f"[yellow]  MCP registration failed: {stderr}[/yellow]")
            console.print(
                f"  Run manually: [dim]claude mcp add repo-brain -- repo-brain serve --root {root.resolve()}[/dim]"
            )


@app.command()
def serve(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Start the MCP server on stdio (for Claude Code / Cursor / Copilot)."""
    import asyncio

    bd = brain_dir(root)
    if not bd.exists():
        console.print("[red]No .repo-brain/ found. Run `repo-brain init` and `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    console.print("[dim]repo-brain MCP server starting on stdio…[/dim]", err=True)
    asyncio.run(run_server(root))


def _section(title: str, count: int) -> None:
    colour = "green" if count else "dim"
    console.print(f"\n[bold {colour}]{title}[/bold {colour}] [{colour}]({count})[/{colour}]")