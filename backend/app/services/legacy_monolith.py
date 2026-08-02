from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


def legacy_system_status() -> dict:
    """Return the current monolith health snapshot.

    This is intentionally thin for Step 1. Later steps will move the logic
    behind this wrapper into dedicated FastAPI services.
    """
    return server.system_status()
