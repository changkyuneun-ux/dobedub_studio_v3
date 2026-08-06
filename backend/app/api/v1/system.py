from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services.studio_api_service import runpod_connection
from backend.app.services.system_status_service import system_status

router = APIRouter(tags=["system"])


@router.get("/system/status")
def get_system_status(_: CurrentUser = Depends(require_permission("system:read"))):
    return system_status()


@router.get("/runpod/connection")
def get_runpod_connection(_: CurrentUser = Depends(require_permission("system:read"))):
    try:
        return runpod_connection()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
