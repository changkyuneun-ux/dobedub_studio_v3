from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.core.config import get_settings
from backend.app.core.security import CurrentUser, require_permission
from backend.app.db.session import get_db
from backend.app.services.audit_log_service import record_audit_log
from backend.app.services.sandbox_pod_service import sandbox_pod_status, start_sandbox_pod, stop_sandbox_pod


router = APIRouter(prefix="/admin/sandbox-pod", tags=["admin"])


@router.get("")
def get_sandbox_pod(_: CurrentUser = Depends(require_permission("sandbox:read"))):
    try:
        return sandbox_pod_status(get_settings())
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/start")
def start_pod(
    request: Request,
    current_user: CurrentUser = Depends(require_permission("sandbox:control")),
    db: Session = Depends(get_db),
):
    try:
        result = start_sandbox_pod(get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor_id=current_user.id,
        action="sandbox_pod.start",
        target_type="sandbox_pod",
        target_id=str(result.get("podId") or ""),
        before=None,
        after={"desiredStatus": result.get("desiredStatus"), "runtimeStatus": result.get("runtimeStatus")},
        ip=request.client.host if request.client else None,
    )
    return result


@router.post("/stop")
def stop_pod(
    request: Request,
    current_user: CurrentUser = Depends(require_permission("sandbox:control")),
    db: Session = Depends(get_db),
):
    try:
        result = stop_sandbox_pod(get_settings())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor_id=current_user.id,
        action="sandbox_pod.stop",
        target_type="sandbox_pod",
        target_id=str(result.get("podId") or ""),
        before=None,
        after={"desiredStatus": result.get("desiredStatus"), "runtimeStatus": result.get("runtimeStatus")},
        ip=request.client.host if request.client else None,
    )
    return result
