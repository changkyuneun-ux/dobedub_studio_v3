from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.app.core.security import CurrentUser, require_permission
from backend.app.services.metadata_loader import ensure_metadata_current
from backend.app.services.metadata_service import get_metadata_status, get_model_metadata, metadata_paths

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/status")
def metadata_status(_: CurrentUser = Depends(require_permission("metadata:read"))):
    return get_metadata_status()


@router.get("/models")
def model_metadata(_: CurrentUser = Depends(require_permission("metadata:read"))):
    return get_model_metadata()


@router.post("/rebuild")
def rebuild_metadata(_: CurrentUser = Depends(require_permission("metadata:rebuild"))):
    return {"ok": True, "manifest": ensure_metadata_current(*metadata_paths(), force=True)}
