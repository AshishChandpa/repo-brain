"""
Tests for MCP tool handler functions.
Each handler is a pure function — no MCP wire protocol needed.
"""
import json
import textwrap
from pathlib import Path

import pytest

from repo_brain.config import save_config, Config
from repo_brain.mcp_server import (
    handle_impact,
    handle_related_files,
    handle_search_symbol,
    handle_status,
    handle_task_context,
    handle_tests,
    _TOOLS,
    make_server,
)


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture()
def indexed_repo(tmp_path: Path) -> Path:
    """A minimal repo that has been init'd and indexed."""
    from repo_brain.scanner import scan, top_level_modules
    from repo_brain.writers.json_writer import write_artifacts
    from repo_brain.writers.markdown_writer import write_markdown
    from repo_brain.models import RepoMap
    from datetime import datetime, timezone

    # create source files
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "__init__.py").write_text("")
    (tmp_path / "app" / "document_service.py").write_text(textwrap.dedent("""
        from fastapi import APIRouter
        router = APIRouter()

        class DocumentService:
            def get_document(self, doc_id: int):
                pass

        @router.get("/documents/{doc_id}")
        def fetch_document(doc_id: int):
            pass

        @router.post("/documents/upload")
        async def upload_document():
            pass
    """))
    (tmp_path / "app" / "audit_log.py").write_text(textwrap.dedent("""
        from app import document_service

        class AuditLog:
            def write_entry(self, msg: str):
                pass
    """))
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_document_service.py").write_text(textwrap.dedent("""
        from app import document_service

        def test_get_document():
            pass

        def test_upload_document():
            pass
    """))

    # init and index
    config = Config()
    bd = tmp_path / ".repo-brain"
    bd.mkdir()
    save_config(config, tmp_path)

    result = scan(tmp_path, config)
    modules = top_level_modules(result.files, tmp_path)
    repo_map = RepoMap(
        project_name="test-project",
        scan_timestamp=datetime.now(timezone.utc).isoformat(),
        python_file_count=len(result.files),
        top_level_modules=modules,
        artifact_paths={},
    )
    write_artifacts(bd, result, repo_map)
    write_markdown(bd, result, repo_map)
    return tmp_path


# ---------------------------------------------------------------------------
# tool registry
# ---------------------------------------------------------------------------

def test_nine_tools_defined():
    assert len(_TOOLS) == 9

def test_tool_names():
    names = {t.name for t in _TOOLS}
    assert names == {
        "repo_brain_status",
        "repo_brain_search_symbol",
        "repo_brain_related_files",
        "repo_brain_impact",
        "repo_brain_tests",
        "repo_brain_task_context",
        "repo_brain_gaps",
        "repo_brain_export_context",
        "repo_brain_route_links",
    }

def test_all_tools_have_description():
    for tool in _TOOLS:
        assert tool.description, f"{tool.name} has no description"

def test_all_tools_have_input_schema():
    for tool in _TOOLS:
        assert tool.inputSchema is not None, f"{tool.name} has no inputSchema"


# ---------------------------------------------------------------------------
# handle_status
# ---------------------------------------------------------------------------

def test_status_returns_file_count(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_status(bd)
    assert result["python_file_count"] >= 3

def test_status_returns_project_name(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_status(bd)
    assert result["project_name"] == "test-project"

def test_status_returns_modules(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_status(bd)
    assert "app" in result["top_level_modules"]

def test_status_returns_routes_count(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_status(bd)
    assert result["routes"] >= 2

def test_status_missing_index(tmp_path):
    bd = tmp_path / ".repo-brain"
    bd.mkdir()
    result = handle_status(bd)
    assert "error" in result


# ---------------------------------------------------------------------------
# handle_search_symbol
# ---------------------------------------------------------------------------

def test_search_symbol_finds_class(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    results = handle_search_symbol(bd, "DocumentService")
    assert any(r["name"] == "DocumentService" for r in results)

def test_search_symbol_case_insensitive(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    results = handle_search_symbol(bd, "documentservice")
    assert any(r["name"] == "DocumentService" for r in results)

def test_search_symbol_substring(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    results = handle_search_symbol(bd, "document")
    names = [r["name"] for r in results]
    assert len(names) >= 1

def test_search_symbol_type_filter(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    results = handle_search_symbol(bd, "document", symbol_type="function")
    assert all(r["symbol_type"] == "function" for r in results)

def test_search_symbol_no_match(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    results = handle_search_symbol(bd, "zzznomatch")
    assert results == []

def test_search_symbol_includes_file_and_line(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    results = handle_search_symbol(bd, "AuditLog")
    assert results[0]["file_path"] != ""
    assert results[0]["lineno"] > 0


# ---------------------------------------------------------------------------
# handle_related_files
# ---------------------------------------------------------------------------

def test_related_files_finds_test(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_related_files(bd, "app/document_service.py")
    assert any("test_document_service" in f for f in result["related_tests"])

def test_related_files_finds_importer(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_related_files(bd, "app/document_service.py")
    assert any("audit_log" in f for f in result["imported_by"])

def test_related_files_likely_affected_union(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_related_files(bd, "app/document_service.py")
    affected = result["likely_affected"]
    assert len(affected) >= 1

def test_related_files_excludes_self(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_related_files(bd, "app/document_service.py")
    assert "app/document_service.py" not in result["likely_affected"]


# ---------------------------------------------------------------------------
# handle_impact
# ---------------------------------------------------------------------------

def test_impact_returns_symbols(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_impact(bd, "app/document_service.py")
    assert any(s["name"] == "DocumentService" for s in result["symbols"])

def test_impact_returns_routes(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_impact(bd, "app/document_service.py")
    assert any(r["path"] in ("/documents/{doc_id}", "/documents/upload") for r in result["routes"])

def test_impact_has_all_keys(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_impact(bd, "app/document_service.py")
    for key in ("target_file", "module_path", "symbols", "routes", "imported_by", "related_tests", "likely_affected"):
        assert key in result


# ---------------------------------------------------------------------------
# handle_tests
# ---------------------------------------------------------------------------

def test_tests_returns_all_when_no_file(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_tests(bd)
    assert len(result) >= 1

def test_tests_filtered_by_file(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_tests(bd, "document_service.py")
    assert all("document" in t["file_path"].lower() for t in result)

def test_tests_includes_functions(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_tests(bd)
    all_fns = [fn for t in result for fn in t["test_functions"]]
    assert "test_get_document" in all_fns or "test_upload_document" in all_fns


# ---------------------------------------------------------------------------
# handle_task_context
# ---------------------------------------------------------------------------

def test_task_context_returns_keywords(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_task_context(bd, "upload document audit logging")
    assert "upload" in result["keywords"] or "document" in result["keywords"]

def test_task_context_suggests_files(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_task_context(bd, "upload document service")
    paths = [f["path"] for f in result["suggested_files"]]
    assert any("document" in p for p in paths)

def test_task_context_suggests_routes(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_task_context(bd, "document upload")
    assert any("upload" in r["path"] for r in result["suggested_routes"])

def test_task_context_has_all_keys(indexed_repo):
    bd = indexed_repo / ".repo-brain"
    result = handle_task_context(bd, "audit log")
    for key in ("task", "keywords", "suggested_files", "suggested_symbols", "suggested_routes", "suggested_tests"):
        assert key in result


# ---------------------------------------------------------------------------
# make_server
# ---------------------------------------------------------------------------

def test_make_server_returns_server(indexed_repo):
    from mcp.server import Server
    server = make_server(indexed_repo)
    assert isinstance(server, Server)

def test_make_server_name(indexed_repo):
    server = make_server(indexed_repo)
    assert server.name == "repo-brain"
