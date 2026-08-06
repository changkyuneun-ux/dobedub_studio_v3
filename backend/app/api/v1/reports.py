from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services import studio_api_service

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", status_code=201)
def create_report(payload: dict, _: CurrentUser = Depends(require_permission("history:read"))):
    return studio_api_service.create_report(payload)


@router.get("/{report_id}")
def get_report(report_id: str, _: CurrentUser = Depends(require_permission("history:read"))):
    try:
        path = studio_api_service.report_path(report_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}") from exc
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=path.name)
