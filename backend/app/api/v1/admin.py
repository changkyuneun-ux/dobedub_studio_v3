from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.security import CurrentUser, require_permission
from backend.app.db.session import get_db
from backend.app.services.admin_service import (
    deactivate_admin_user,
    list_admin_users,
    list_admin_workflows,
    list_permission_governance,
    register_admin_workflow,
    reset_admin_user_password,
    set_admin_workflow_active,
    upsert_admin_user,
)
from backend.app.services.permission_service import update_role_permission_codes
router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users")
def users(_: CurrentUser = Depends(require_permission("users:read")), db: Session = Depends(get_db)):
    try:
        return list_admin_users(db)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"User list failed: {exc}") from exc


@router.get("/permissions")
def permissions(_: CurrentUser = Depends(require_permission("roles:read")), db: Session = Depends(get_db)):
    try:
        return list_permission_governance(db)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Permission governance load failed: {exc}") from exc


@router.put("/roles/{role_code}/permissions")
def update_role_permissions(role_code: str, payload: dict, _: CurrentUser = Depends(require_permission("roles:write")), db: Session = Depends(get_db)):
    try:
        return update_role_permission_codes(db, role_code, payload.get("permissionCodes") or payload.get("permissions") or [])
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Role permission save failed: {exc}") from exc


@router.post("/users")
def create_user(payload: dict, _: CurrentUser = Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    try:
        return upsert_admin_user(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"User save failed: {exc}") from exc


@router.put("/users/{user_id}")
def update_user(user_id: str, payload: dict, _: CurrentUser = Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    try:
        return upsert_admin_user(db, payload, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"User save failed: {exc}") from exc


@router.post("/users/{user_id}/deactivate")
def deactivate_user(user_id: str, _: CurrentUser = Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    try:
        return deactivate_admin_user(db, user_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"User deactivate failed: {exc}") from exc


@router.post("/users/{user_id}/reset-password")
def reset_password(user_id: str, payload: dict, _: CurrentUser = Depends(require_permission("users:write")), db: Session = Depends(get_db)):
    try:
        return reset_admin_user_password(db, user_id, str(payload.get("password") or ""))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Password reset failed: {exc}") from exc


@router.get("/workflows")
def workflows(_: CurrentUser = Depends(require_permission("workflows:read"))):
    try:
        return list_admin_workflows()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflows")
def register_workflow(payload: dict, _: CurrentUser = Depends(require_permission("workflows:write"))):
    try:
        return register_admin_workflow(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/activate")
def activate_workflow(workflow_id: str, _: CurrentUser = Depends(require_permission("workflows:activate"))):
    try:
        return set_admin_workflow_active(workflow_id, True)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/workflows/{workflow_id}/deactivate")
def deactivate_workflow(workflow_id: str, _: CurrentUser = Depends(require_permission("workflows:activate"))):
    try:
        return set_admin_workflow_active(workflow_id, False)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
