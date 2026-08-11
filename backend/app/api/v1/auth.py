from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.security import CurrentUser, current_user_from_headers
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.services.admin_service import admin_login, admin_user_payload
from backend.app.services.audit_log_service import record_audit_log

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
# A-05: 접근 이력(로그인 시도)은 별도 테이블을 만들지 않고 A-04의 audit_logs에
# action="login"으로 흡수한다. 성공/실패 모두 기록하되, 실패 시 비밀번호 등
# 민감정보는 남기지 않는다(사유 메시지만 after_json에 저장).
def login(payload: dict, request: Request, db: Session = Depends(get_db)):
    submitted_id = str(payload.get("id") or "").strip() or None
    ip = request.client.host if request.client else None
    try:
        result = admin_login(db, payload)
    except ValueError as exc:
        record_audit_log(
            db,
            actor_id=submitted_id,
            action="login",
            target_type="user",
            target_id=submitted_id,
            before=None,
            after={"success": False, "reason": str(exc)},
            ip=ip,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Login failed: {exc}") from exc
    logged_in_id = str((result.get("user") or {}).get("id") or submitted_id or "")
    record_audit_log(
        db,
        actor_id=logged_in_id or None,
        action="login",
        target_type="user",
        target_id=logged_in_id or None,
        before=None,
        after={"success": True},
        ip=ip,
    )
    return result


@router.get("/session")
def session(current_user: CurrentUser = Depends(current_user_from_headers), db: Session = Depends(get_db)):
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    try:
        return {"user": admin_user_payload(db, user)}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Session refresh failed: {exc}") from exc
