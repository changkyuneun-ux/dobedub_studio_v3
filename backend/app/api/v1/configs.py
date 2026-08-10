from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.security import CurrentUser, require_any_permission, require_permission
from backend.app.services import studio_api_service

# UI 미연결 · 외부 연동 및 향후 화면용으로 유지 (2026-08 결정, D-01)
# 프론트는 이 엔드포인트를 호출하지 않는다. 삭제하지 말 것 - config_snapshots
# 테이블과 서비스 코드(studio_api_service.load_configs/append_config/
# create_config_snapshot)도 동일하게 유지 대상이다.
router = APIRouter(prefix="/configs", tags=["configs"])


@router.get("")
def configs(_: CurrentUser = Depends(require_any_permission(("workflows:read", "history:read")))):
    return {"items": studio_api_service.load_configs()}


@router.post("", status_code=201)
def create_config(payload: dict, _: CurrentUser = Depends(require_permission("workflows:write"))):
    return studio_api_service.create_config_snapshot(payload)
