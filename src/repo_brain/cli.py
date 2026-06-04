from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from repo_brain.config import Config, brain_dir, load_config, save_config
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
