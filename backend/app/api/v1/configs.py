from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.security import CurrentUser, require_any_permission, require_permission
from backend.app.services import studio_api_service

router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("")
def configs(_: CurrentUser = Depends(require_any_permission(("workflows:read", "history:read")))):
    return {"items": studio_api_service.load_configs()}


@router.post("", status_code=201)
def create_config(payload: dict, _: CurrentUser = Depends(require_permission("workflows:write"))):
    return studio_api_service.create_config_snapshot(payload)
