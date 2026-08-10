from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services import studio_api_service

# UI 미연결 · 외부 연동 및 향후 화면용으로 유지 (2026-08 결정, D-01)
# 프론트는 이 엔드포인트를 호출하지 않는다. 삭제하지 말 것 - reports 테이블과
# 서비스 코드(studio_api_service.create_report/report_markdown/report_path)도
# 동일하게 유지 대상이다.
router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", status_code=201)
def create_report(payload: dict, _: CurrentUser = Depends(require_permission("history:read"))):
    return studio_api_service.create_report(payload)


@router.get("/{report_id}")
def get_report(report_id: str, _: CurrentUser = Depends(require_permission("history:read"))):
    try:
        path = studio_api_service.report_path(report_id)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Report not found: {report_id}") from exc
    return FileResponse(path, media_type="text/markdown; charset=utf-8", filename=path.name)
