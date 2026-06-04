from __future__ import annotations

import importlib.resources as pkg_resources
import json
import shutil
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from repo_brain.config import Config, brain_dir, load_config, save_config
from repo_brain.context import build_context, load_context_artifacts
from repo_brain.impact import analyse, load_impact_artifacts
from repo_brain.mcp_server import run_server
from repo_brain.models import RepoMap
from repo_brain.scanner import scan, top_level_modules
from repo_brain.writers.json_writer import write_artifacts
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
) -> None:
    """Scan the repository and generate context artifacts."""
    bd = brain_dir(root)
    if not bd.exists():
        console.print("[red]Run `repo-brain init` first.[/red]")
        raise typer.Exit(1)

    config = load_config(root)

    with console.status("[bold green]Scanning repository…[/bold green]"):
        result = scan(root, config)

    modules = top_level_modules(result.files, root)
    timestamp = datetime.now(timezone.utc).isoformat()

    repo_map = RepoMap(
        project_name=config.project_name,
        scan_timestamp=timestamp,
        python_file_count=len(result.files),
        top_level_modules=modules,
        artifact_paths={
            "repo_map": str(bd / "repo_map.json"),
            "symbols": str(bd / "symbols.json"),
            "imports": str(bd / "imports.json"),
            "routes": str(bd / "routes.json"),
            "tests": str(bd / "tests.json"),
            "markdown": str(bd / "REPO_MAP.md"),
        },
    )

    write_artifacts(bd, result, repo_map)
    write_markdown(bd, result, repo_map)

    console.print(f"[green]Indexed {len(result.files)} Python files.[/green]")
    console.print(f"  Symbols : {len(result.symbols)}")
    console.print(f"  Imports : {len(result.imports)}")
    console.print(f"  Routes  : {len(result.routes)}")
    console.print(f"  Tests   : {len(result.tests)} test file(s)")
    console.print(f"\nArtifacts written to [bold]{bd.resolve()}[/bold]")


@app.command(name="map")
def repo_map(
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Print a readable repository summary from existing artifacts."""
    import json

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

    table = Table(title="Repository Map", show_header=False, box=None, padding=(0, 2))
    table.add_column("Key", style="bold cyan")
    table.add_column("Value")

    project = data.get("project_name") or "[dim]unnamed[/dim]"
    table.add_row("Project", project)
    table.add_row("Python files", str(data.get("python_file_count", 0)))
    table.add_row("Classes", str(classes))
    table.add_row("Functions", str(functions))
    table.add_row("FastAPI routes", str(routes_count))
    table.add_row("Test files", str(test_file_count))
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
    """Show what is affected if a file changes."""
    bd = brain_dir(root)

    if not (bd / "symbols.json").exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    # normalise to a path string relative to root
    try:
        target = str(file.relative_to(root))
    except ValueError:
        target = str(file)

    symbols, routes, imports, tests = load_impact_artifacts(bd)
    result = analyse(target, symbols, routes, imports, tests)

    # ── header ──────────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        f"[bold]{result.target_file}[/bold]\n[dim]module: {result.module_path or '—'}[/dim]",
        title="[bold cyan]Impact Analysis[/bold cyan]",
        expand=False,
    ))

    # ── symbols defined here ─────────────────────────────────────────────────
    _section("Symbols defined in this file", len(result.symbols))
    for s in result.symbols:
        kind = f"[dim]{s.symbol_type}[/dim]"
        parent = f"  [dim](in {s.parent})[/dim]" if s.parent else ""
        console.print(f"  {kind}  [bold]{s.name}[/bold]{parent}  [dim]line {s.lineno}[/dim]")

    # ── routes defined here ──────────────────────────────────────────────────
    _section("FastAPI routes defined in this file", len(result.routes))
    for r in result.routes:
        console.print(f"  [green]{r.method.upper()}[/green]  {r.path}  [dim]→ {r.function_name}[/dim]")

    # ── imported by ──────────────────────────────────────────────────────────
    _section("Imported by", len(result.imported_by))
    for f in result.imported_by:
        console.print(f"  [yellow]{f}[/yellow]")

    # ── related tests ────────────────────────────────────────────────────────
    _section("Related tests", len(result.related_tests))
    for f in result.related_tests:
        console.print(f"  [magenta]{f}[/magenta]")

    # ── likely affected ──────────────────────────────────────────────────────
    _section("Likely affected files", len(result.likely_affected))
    for f in result.likely_affected:
        console.print(f"  • {f}")

    if not result.likely_affected:
        console.print("  [dim]No other files appear to depend on this file.[/dim]")

    # ── write artifact ───────────────────────────────────────────────────────
    out = bd / "last_impact.json"
    out.write_text(json.dumps(result.model_dump(), indent=2), encoding="utf-8")
    console.print(f"\n[dim]Saved to {out.resolve()}[/dim]")


@app.command()
def context(
    task: str = typer.Argument(..., help="Natural-language task description"),
    root: Path = typer.Option(Path("."), "--root", help="Repository root"),
) -> None:
    """Suggest files, symbols, routes and tests relevant to a task."""
    bd = brain_dir(root)

    if not (bd / "symbols.json").exists():
        console.print("[red]No index found. Run `repo-brain index` first.[/red]")
        raise typer.Exit(1)

    symbols, routes, imports, tests = load_context_artifacts(bd)
    result = build_context(task, symbols, routes, imports, tests)

    console.print()
    console.print(Panel(
        f'[bold]"{result.task}"[/bold]\n[dim]keywords: {", ".join(result.keywords) or "none matched"}[/dim]',
        title="[bold cyan]Task Context[/bold cyan]",
        expand=False,
    ))

    if not result.keywords:
        console.print("[yellow]No meaningful keywords found. Try a more specific task description.[/yellow]")
        raise typer.Exit(0)

    # ── suggested files ──────────────────────────────────────────────────────
    _section("Suggested files to read", len(result.suggested_files))
    for sf in result.suggested_files:
        bar = "█" * sf.score
        console.print(f"  [yellow]{sf.path}[/yellow]  [dim]{bar} ({sf.score})[/dim]")

    # ── suggested symbols ────────────────────────────────────────────────────
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

    # ── suggested routes ─────────────────────────────────────────────────────
    _section("Suggested routes", len(result.suggested_routes))
    for r in result.suggested_routes:
        console.print(
            f"  [green]{r.method.upper()}[/green]  {r.path}"
            f"  [dim]→ {r.function_name}  ({r.file_path})[/dim]"
        )

    # ── suggested tests ──────────────────────────────────────────────────────
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

    # ── write artifact ───────────────────────────────────────────────────────
    out = bd / "last_context.json"
    out.write_text(json.dumps(result.model_dump(), indent=2), encoding="utf-8")
    console.print(f"\n[dim]Saved to {out.resolve()}[/dim]")


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

    # ── 2. index ─────────────────────────────────────────────────────────────
    config = load_config(root)
    with console.status("[bold green]Indexing repository…[/bold green]"):
        result = scan(root, config)

    modules = top_level_modules(result.files, root)
    timestamp = datetime.now(timezone.utc).isoformat()
    repo_map = RepoMap(
        project_name=config.project_name,
        scan_timestamp=timestamp,
        python_file_count=len(result.files),
        top_level_modules=modules,
        artifact_paths={
            "repo_map": str(bd / "repo_map.json"),
            "symbols": str(bd / "symbols.json"),
            "imports": str(bd / "imports.json"),
            "routes": str(bd / "routes.json"),
            "tests": str(bd / "tests.json"),
            "markdown": str(bd / "REPO_MAP.md"),
        },
    )
    write_artifacts(bd, result, repo_map)
    write_markdown(bd, result, repo_map)
    console.print(
        f"[green]✓ Indexed {len(result.files)} Python files[/green]"
        f"  [dim]({len(result.symbols)} symbols · {len(result.routes)} routes · {len(result.tests)} test files)[/dim]"
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


def _install_skills(commands_dir: Path) -> tuple[list[str], list[str]]:
    """Copy bundled skill files to .claude/commands/. Returns (installed, skipped)."""
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
    """Register repo-brain as an MCP server with the Claude Code CLI."""
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
        # 'already exists' is not a real failure
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
