from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel

BRAIN_DIR = ".repo-brain"
CONFIG_FILE = "config.json"


class Config(BaseModel):
    project_name: str | None = None
    source_roots: list[str] = ["."]
    exclude_dirs: list[str] = [
        ".git",
        ".venv",
        "venv",
        "__pycache__",
        ".mypy_cache",
        ".pytest_cache",
        "node_modules",
        ".repo-brain",
    ]
    include_extensions: list[str] = [".py"]


def brain_dir(root: Path = Path(".")) -> Path:
    return root / BRAIN_DIR


def config_path(root: Path = Path(".")) -> Path:
    return brain_dir(root) / CONFIG_FILE


def load_config(root: Path = Path(".")) -> Config:
    path = config_path(root)
    if not path.exists():
        return Config()
    return Config.model_validate_json(path.read_text())


def save_config(config: Config, root: Path = Path(".")) -> None:
    path = config_path(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))
