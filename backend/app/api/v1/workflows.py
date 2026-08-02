from __future__ import annotations

from fastapi import APIRouter, HTTPException

from backend.app.services.workflow_service import (
    get_segment_defaults,
    get_widget_metadata,
    get_workflow_schema,
    list_workflows,
)

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("")
def workflows():
    return list_workflows()


@router.get("/{workflow_id}/schema")
def workflow_schema(workflow_id: str):
    try:
        return get_workflow_schema(workflow_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}") from exc


@router.get("/{workflow_id}/segment-defaults")
def workflow_segment_defaults(workflow_id: str):
    try:
        return get_segment_defaults(workflow_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Segment defaults not found: {workflow_id}") from exc


@router.get("/{workflow_id}/widget-metadata")
def workflow_widget_metadata(workflow_id: str):
    try:
        return get_widget_metadata(workflow_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Workflow not found: {workflow_id}") from exc
