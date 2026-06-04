from __future__ import annotations

import json
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


def _section(title: str, count: int) -> None:
    colour = "green" if count else "dim"
    console.print(f"\n[bold {colour}]{title}[/bold {colour}] [{colour}]({count})[/{colour}]")
