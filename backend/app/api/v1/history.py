from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services import studio_api_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
# B-01: 기본값을 설계(3a) 기준인 20으로 통일. 50은 프론트가 사용자에게 제공하는
# 선택지 중 하나로만 남는다 - 프론트는 이제 20/50 중 사용자가 고른 값을 항상
# 명시 전송하므로 이 기본값은 pageSize를 아예 안 보내는 다른 호출자(스크립트,
# 향후 API 클라이언트 등)를 위한 안전망이다.
def history(page: int = 1, pageSize: int = 20, _: CurrentUser = Depends(require_permission("history:read"))):
    return studio_api_service.paginated_history(page, pageSize)


@router.post("/{task_id}/delete")
def delete_history_item(task_id: str, _: CurrentUser = Depends(require_permission("history:delete"))):
    try:
        return studio_api_service.delete_history_item(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"History item not found: {task_id}") from exc
