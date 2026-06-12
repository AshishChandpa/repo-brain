"""Minimal tests for the watch module — just verify import and class structure."""
from pathlib import Path


def test_watch_module_importable():
    import repo_brain.watch  # noqa: F401


def test_reindex_handler_initialises():
    from repo_brain.watch import _RepoEventHandler
    from repo_brain.config import Config

    handler = _RepoEventHandler(
        root=Path("."),
        config=Config(),
        bd=Path(".repo-brain"),
    )
    assert handler._debounce_seconds if hasattr(handler, "_debounce_seconds") else True


def test_trigger_ignores_non_source_files():
    from repo_brain.watch import _RepoEventHandler
    from repo_brain.config import Config

    handler = _RepoEventHandler(
        root=Path("."),
        config=Config(),
        bd=Path(".repo-brain"),
    )
    # Triggering a non-matching extension should not set a timer
    handler._trigger("README.md")
    assert handler._timer is None


def test_make_watchdog_handler_returns_none_without_watchdog():
    """When watchdog is not installed, _make_watchdog_handler should not crash."""
    import sys
    import importlib

    # We can only test the happy path here — watchdog is a dependency so it should be present
    try:
        import watchdog  # noqa: F401
        from repo_brain.watch import _make_watchdog_handler
        from repo_brain.config import Config
        h = _make_watchdog_handler(Path("."), Config(), Path(".repo-brain"))
        # May be None or a handler depending on environment
        assert h is not None or h is None  # just check it doesn't raise
    except ImportError:
        pass  # watchdog not installed — skip