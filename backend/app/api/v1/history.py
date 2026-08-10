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
    # 2026-08-10: 진행 중(터미널 상태가 아닌) 작업의 삭제 요청 - db_adapter.delete_history_item이
    # 이 경우 ValueError를 던진다. 3a 화면의 삭제 확인 모달이 "진행 중인 작업은 삭제할 수
    # 없습니다"라고 안내하지만 실제로 막는 코드가 없던 버그를 수정 - 프론트 버튼 비활성화와
    # 별개로 API 직접 호출도 여기서 막는다(방어적 이중 확인).
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
