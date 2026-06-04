import textwrap
from pathlib import Path

import pytest

from repo_brain.config import Config
from repo_brain.scanner import scan, top_level_modules


@pytest.fixture()
def sample_repo(tmp_path: Path) -> Path:
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "main.py").write_text(textwrap.dedent("""
        from fastapi import FastAPI
        app = FastAPI()

        @app.get("/health")
        def health():
            return {"status": "ok"}
    """))
    (tmp_path / "app" / "models.py").write_text(textwrap.dedent("""
        class User:
            def __init__(self, name: str):
                self.name = name
    """))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_main.py").write_text(textwrap.dedent("""
        def test_health():
            assert True
    """))
    return tmp_path


def test_scan_finds_py_files(sample_repo):
    config = Config()
    result = scan(sample_repo, config)
    paths = [f.path for f in result.files]
    assert any("main.py" in p for p in paths)
    assert any("models.py" in p for p in paths)
    assert any("test_main.py" in p for p in paths)


def test_scan_marks_test_files(sample_repo):
    config = Config()
    result = scan(sample_repo, config)
    test_files = [f for f in result.files if f.is_test]
    assert len(test_files) == 1
    assert "test_main.py" in test_files[0].path


def test_scan_detects_route(sample_repo):
    config = Config()
    result = scan(sample_repo, config)
    assert any(r.method == "get" and r.path == "/health" for r in result.routes)


def test_scan_detects_class(sample_repo):
    config = Config()
    result = scan(sample_repo, config)
    assert any(s.name == "User" and s.symbol_type == "class" for s in result.symbols)


def test_scan_detects_test_function(sample_repo):
    config = Config()
    result = scan(sample_repo, config)
    assert any("test_health" in t.test_functions for t in result.tests)


def test_scan_excludes_dirs(sample_repo):
    (sample_repo / "__pycache__").mkdir()
    (sample_repo / "__pycache__" / "cached.py").write_text("x = 1")
    config = Config()
    result = scan(sample_repo, config)
    assert not any("__pycache__" in f.path for f in result.files)


def test_top_level_modules(sample_repo):
    config = Config()
    result = scan(sample_repo, config)
    modules = top_level_modules(result.files, sample_repo)
    assert "app" in modules
    assert "tests" in modules
