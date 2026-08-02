from __future__ import annotations

from fastapi import APIRouter

from backend.app.services.metadata_service import get_metadata_status, get_model_metadata

router = APIRouter(prefix="/metadata", tags=["metadata"])


@router.get("/status")
def metadata_status():
    return get_metadata_status()


@router.get("/models")
def model_metadata():
    return get_model_metadata()
