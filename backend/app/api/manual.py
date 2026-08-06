from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services.manual_service import manual_html_page

router = APIRouter(tags=["manual"])


@router.get("/manual", response_class=HTMLResponse)
def manual(_: CurrentUser = Depends(require_permission("manual:read"))):
    try:
        return manual_html_page()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"Manual not found: {exc}") from exc
