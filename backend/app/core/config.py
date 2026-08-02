from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    app_name: str = "DOBEDUB STUDIO API"
    api_prefix: str = "/api/v1"
    project_root: Path = PROJECT_ROOT
    workflows_dir: Path = PROJECT_ROOT / "workflows"
    data_dir: Path = PROJECT_ROOT / "data"
    metadata_dir: Path = PROJECT_ROOT / "metadata"
    dry_run: bool = True


def get_settings() -> Settings:
    dry_run = os.environ.get("RUNPOD_DRY_RUN", "1") != "0"
    return Settings(
        workflows_dir=Path(os.environ.get("WORKFLOWS_DIR", PROJECT_ROOT / "workflows")),
        data_dir=Path(os.environ.get("STUDIO_DATA_DIR", PROJECT_ROOT / "data")),
        metadata_dir=Path(os.environ.get("METADATA_DIR", PROJECT_ROOT / "metadata")),
        dry_run=dry_run,
    )
