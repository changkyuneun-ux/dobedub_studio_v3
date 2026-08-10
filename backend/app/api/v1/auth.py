from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.security import CurrentUser, current_user_from_headers
from backend.app.db.models import User
from backend.app.db.session import get_db
from backend.app.services.admin_service import admin_login, admin_user_payload

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(payload: dict, db: Session = Depends(get_db)):
    try:
        return admin_login(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Login failed: {exc}") from exc


@router.get("/session")
def session(current_user: CurrentUser = Depends(current_user_from_headers), db: Session = Depends(get_db)):
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid or expired session")
    try:
        return {"user": admin_user_payload(db, user)}
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Session refresh failed: {exc}") from exc
