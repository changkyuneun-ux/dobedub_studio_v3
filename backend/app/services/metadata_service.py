from __future__ import annotations

from backend.app.core.config import get_settings
from backend.app.services.metadata_loader import (
    metadata_status as load_metadata_status,
    model_metadata as load_model_metadata,
    workflow_widget_metadata as load_workflow_widget_metadata,
)


def metadata_paths():
    settings = get_settings()
    bundled_segment_defaults_path = settings.project_root / "data" / "segment-defaults.json"
    return (
        settings.project_root,
        settings.workflows_dir,
        settings.data_dir,
        settings.metadata_dir,
        bundled_segment_defaults_path,
    )


def get_metadata_status() -> dict:
    return load_metadata_status(*metadata_paths())


def get_model_metadata() -> dict:
    return load_model_metadata(*metadata_paths())


def get_workflow_widget_metadata(workflow_id: str) -> dict:
    return load_workflow_widget_metadata(workflow_id, *metadata_paths())
