from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.config import get_settings
from backend.app.core.security import CurrentUser, require_permission
from backend.app.services.sandbox_pod_service import sandbox_pod_status, start_sandbox_pod, stop_sandbox_pod


router = APIRouter(prefix="/admin/sandbox-pod", tags=["admin"])


@router.get("")
def get_sandbox_pod(_: CurrentUser = Depends(require_permission("sandbox:read"))):
    try:
        return sandbox_pod_status(get_settings())
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/start")
def start_pod(_: CurrentUser = Depends(require_permission("sandbox:control"))):
    try:
        return start_sandbox_pod(get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/stop")
def stop_pod(_: CurrentUser = Depends(require_permission("sandbox:control"))):
    try:
        return stop_sandbox_pod(get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
