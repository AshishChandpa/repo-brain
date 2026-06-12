from __future__ import annotations

import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

from repo_brain.config import Config, brain_dir, load_config
from repo_brain.models import RepoMap
from repo_brain.scanner import file_counts_by_language, scan_incremental, top_level_modules
from repo_brain.writers.json_writer import write_artifacts, write_hashes
from repo_brain.writers.markdown_writer import write_markdown

console = Console()

_DEBOUNCE_SECONDS = 1.5


def watch(root: Path) -> None:
    """Watch the repository for file changes and auto re-index."""
    try:
        from watchdog.events import FileSystemEventHandler
        from watchdog.observers import Observer
    except ImportError:
        console.print(
            "[red]watchdog is required for `repo-brain watch`.[/red]\n"
            "Install it: [bold]pip install watchdog[/bold]"
        )
        return

    config = load_config(root)
    bd = brain_dir(root)

    console.print(f"[bold green]Watching[/bold green] {root.resolve()}")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    handler = _RepoEventHandler(root, config, bd)
    observer = Observer()

    for source_root in config.source_roots:
        watch_dir = (root / source_root).resolve()
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        console.print("\n[dim]Stopped watching.[/dim]")


class _RepoEventHandler:
    def __init__(self, root: Path, config: Config, bd: Path) -> None:
        self._root = root
        self._config = config
        self._bd = bd
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()
        self._extensions = set(config.include_extensions)

    # watchdog calls these
    def dispatch(self, event) -> None:
        pass

    def on_modified(self, event) -> None:
        self._trigger(getattr(event, "src_path", ""))

    def on_created(self, event) -> None:
        self._trigger(getattr(event, "src_path", ""))

    def on_deleted(self, event) -> None:
        self._trigger(getattr(event, "src_path", ""))

    def _trigger(self, path: str) -> None:
        if path and not any(path.endswith(ext) for ext in self._extensions):
            return
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(_DEBOUNCE_SECONDS, self._reindex)
            self._timer.start()

    def _reindex(self) -> None:
        try:
            result, new_hashes = scan_incremental(self._root, self._config, self._bd)
            modules = top_level_modules(result.files, self._root)
            lang_counts = file_counts_by_language(result.files)
            timestamp = datetime.now(timezone.utc).isoformat()
            repo_map = RepoMap(
                project_name=self._config.project_name,
                scan_timestamp=timestamp,
                python_file_count=lang_counts.get("python", 0),
                file_counts=lang_counts,
                top_level_modules=modules,
                artifact_paths={
                    "repo_map": str(self._bd / "repo_map.json"),
                    "symbols": str(self._bd / "symbols.json"),
                    "imports": str(self._bd / "imports.json"),
                    "routes": str(self._bd / "routes.json"),
                    "tests": str(self._bd / "tests.json"),
                    "call_graph": str(self._bd / "call_graph.json"),
                    "markdown": str(self._bd / "REPO_MAP.md"),
                },
            )
            write_artifacts(self._bd, result, repo_map)
            write_hashes(self._bd, new_hashes)
            write_markdown(self._bd, result, repo_map)
            ts = datetime.now().strftime("%H:%M:%S")
            console.print(
                f"[dim]{ts}[/dim] [green]Re-indexed[/green]  "
                f"[dim]{len(result.files)} files · {len(result.symbols)} symbols[/dim]"
            )
        except Exception as exc:
            console.print(f"[red]Re-index failed:[/red] {exc}")


# Make the handler a proper watchdog FileSystemEventHandler when watchdog is available
def _make_watchdog_handler(root: Path, config: Config, bd: Path):
    try:
        from watchdog.events import FileSystemEventHandler

        class _Handler(_RepoEventHandler, FileSystemEventHandler):
            def __init__(self):
                _RepoEventHandler.__init__(self, root, config, bd)
                FileSystemEventHandler.__init__(self)

            def on_modified(self, event):
                if not event.is_directory:
                    self._trigger(event.src_path)

            def on_created(self, event):
                if not event.is_directory:
                    self._trigger(event.src_path)

            def on_deleted(self, event):
                if not event.is_directory:
                    self._trigger(event.src_path)

        return _Handler()
    except ImportError:
        return None


def watch(root: Path) -> None:  # noqa: F811  (redefines for real implementation)
    """Watch the repository for file changes and auto re-index."""
    try:
        from watchdog.observers import Observer
    except ImportError:
        console.print(
            "[red]watchdog is required for `repo-brain watch`.[/red]\n"
            "Install it: [bold]pip install watchdog[/bold]"
        )
        return

    config = load_config(root)
    bd = brain_dir(root)

    console.print(f"[bold green]Watching[/bold green] {root.resolve()}")
    console.print("[dim]Press Ctrl+C to stop.[/dim]\n")

    handler = _make_watchdog_handler(root, config, bd)
    if handler is None:
        console.print("[red]Could not create file watcher.[/red]")
        return

    observer = Observer()
    for source_root in config.source_roots:
        watch_dir = (root / source_root).resolve()
        if watch_dir.exists():
            observer.schedule(handler, str(watch_dir), recursive=True)

    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join()
        console.print("\n[dim]Stopped watching.[/dim]")
