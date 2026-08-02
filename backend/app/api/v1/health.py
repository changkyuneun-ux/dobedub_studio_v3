from __future__ import annotations

from fastapi import APIRouter

from backend.app.core.config import get_settings
from backend.app.services.legacy_monolith import legacy_system_status

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    settings = get_settings()
    legacy_status = legacy_system_status()
    return {
        "ok": legacy_status.get("ok", False),
        "app": "dobedub-studio",
        "backend": "fastapi",
        "dryRun": settings.dry_run,
        "workflowsDir": str(settings.workflows_dir),
        "dataDir": str(settings.data_dir),
        "metadataDir": str(settings.metadata_dir),
        "legacy": legacy_status,
    }
