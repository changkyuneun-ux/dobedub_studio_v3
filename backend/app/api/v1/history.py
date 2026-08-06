from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services import studio_api_service

router = APIRouter(prefix="/history", tags=["history"])


@router.get("")
def history(page: int = 1, pageSize: int = 50, _: CurrentUser = Depends(require_permission("history:read"))):
    return studio_api_service.paginated_history(page, pageSize)


@router.post("/{task_id}/delete")
def delete_history_item(task_id: str, _: CurrentUser = Depends(require_permission("history:delete"))):
    try:
        return studio_api_service.delete_history_item(task_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"History item not found: {task_id}") from exc
