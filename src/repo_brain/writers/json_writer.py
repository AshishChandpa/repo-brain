from __future__ import annotations

import json
from pathlib import Path

from repo_brain.models import RepoMap, ScanResult


def write_artifacts(
    brain_dir: Path,
    result: ScanResult,
    repo_map: RepoMap,
) -> None:
    brain_dir.mkdir(parents=True, exist_ok=True)

    _write_json(brain_dir / "repo_map.json", repo_map.model_dump())
    _write_json(brain_dir / "symbols.json", [s.model_dump() for s in result.symbols])
    _write_json(brain_dir / "imports.json", [i.model_dump() for i in result.imports])
    _write_json(brain_dir / "routes.json", [r.model_dump() for r in result.routes])
    _write_json(brain_dir / "tests.json", [t.model_dump() for t in result.tests])
    _write_json(brain_dir / "call_graph.json", [c.model_dump() for c in result.calls])
    _write_json(brain_dir / "route_links.json", [rl.model_dump() for rl in result.route_links])


def write_hashes(brain_dir: Path, hashes: dict[str, str]) -> None:
    _write_json(brain_dir / "file_hashes.json", hashes)


def _write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, indent=2), encoding="utf-8")
