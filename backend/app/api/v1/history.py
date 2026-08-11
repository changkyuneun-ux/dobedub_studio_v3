from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from backend.app.core.security import CurrentUser, require_permission
from backend.app.db.models import WorkflowTask
from backend.app.db.session import get_db
from backend.app.services import studio_api_service
from backend.app.services.audit_log_service import record_audit_log

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
# B-01: 기본값을 설계(3a) 기준인 20으로 통일. 50은 프론트가 사용자에게 제공하는
# 선택지 중 하나로만 남는다 - 프론트는 이제 20/50 중 사용자가 고른 값을 항상
# 명시 전송하므로 이 기본값은 pageSize를 아예 안 보내는 다른 호출자(스크립트,
# 향후 API 클라이언트 등)를 위한 안전망이다.
def history(page: int = 1, pageSize: int = 20, _: CurrentUser = Depends(require_permission("history:read"))):
    return studio_api_service.paginated_history(page, pageSize)


@router.post("/{task_id}/delete")
def delete_history_item(
    task_id: str,
    request: Request,
    current_user: CurrentUser = Depends(require_permission("history:delete")),
    db: Session = Depends(get_db),
):
    # A-04: 삭제 전에 최소한의 스냅샷을 남긴다 - studio_api_service.delete_history_item은
    # 자체 세션(history_repository())으로 실제 삭제를 수행하므로, 여기서는 별도 세션(db)으로
    # 삭제 직전 상태만 조회해 감사 로그의 before_json에 담는다.
    task = db.get(WorkflowTask, task_id)
    before = {"taskId": task_id, "status": task.status, "workflowId": task.workflow_id} if task else None
    try:
        result = studio_api_service.delete_history_item(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"History item not found: {task_id}") from exc
    # 2026-08-10: 진행 중(터미널 상태가 아닌) 작업의 삭제 요청 - db_adapter.delete_history_item이
    # 이 경우 ValueError를 던진다. 3a 화면의 삭제 확인 모달이 "진행 중인 작업은 삭제할 수
    # 없습니다"라고 안내하지만 실제로 막는 코드가 없던 버그를 수정 - 프론트 버튼 비활성화와
    # 별개로 API 직접 호출도 여기서 막는다(방어적 이중 확인).
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    record_audit_log(
        db,
        actor_id=current_user.id,
        action="history.delete",
        target_type="history_item",
        target_id=task_id,
        before=before,
        after={"deleted": True},
        ip=request.client.host if request.client else None,
    )
    return result
