from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services.workflow_service import (
    get_segment_defaults,
    get_workflow_schema,
    list_workflows,
)
from backend.app.services.metadata_service import get_workflow_widget_metadata as get_widget_metadata

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
def workflows(_: CurrentUser = Depends(require_permission("workflows:read"))):
    return list_workflows()


@router.get("/{workflow_id}/schema")
def workflow_schema(workflow_id: str, _: CurrentUser = Depends(require_permission("workflows:read"))):
    try:
        return get_workflow_schema(workflow_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}") from exc


@router.get("/{workflow_id}/segment-defaults")
def workflow_segment_defaults(workflow_id: str, _: CurrentUser = Depends(require_permission("workflows:read"))):
    try:
        return get_segment_defaults(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Segment defaults not found: {workflow_id}") from exc


@router.get("/{workflow_id}/widget-metadata")
def workflow_widget_metadata(workflow_id: str, _: CurrentUser = Depends(require_permission("metadata:read"))):
    try:
        return get_widget_metadata(workflow_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}") from exc
