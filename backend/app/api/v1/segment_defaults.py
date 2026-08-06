from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.security import CurrentUser, require_permission
from backend.app.core.config import get_settings
from backend.app.services.segment_defaults_loader import get_workflow_segment_defaults, load_segment_defaults

router = APIRouter(prefix="/segment-defaults", tags=["segment-defaults"])


def bundled_segment_defaults_path():
    return get_settings().project_root / "data" / "segment-defaults.json"


@router.get("")
def segment_defaults(_: CurrentUser = Depends(require_permission("workflows:read"))):
    settings = get_settings()
    return load_segment_defaults(settings.data_dir, bundled_segment_defaults_path())


@router.get("/{workflow_id}")
def workflow_segment_defaults(workflow_id: str, _: CurrentUser = Depends(require_permission("workflows:read"))):
    settings = get_settings()
    try:
        return get_workflow_segment_defaults(workflow_id, settings.data_dir, bundled_segment_defaults_path())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Segment defaults not found: {workflow_id}") from exc
