from __future__ import annotations

import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import server  # noqa: E402


def list_workflows() -> list[dict]:
    return server.list_workflows()


def get_workflow_schema(workflow_id: str) -> dict:
    return server.workflow_schema(workflow_id)


def get_segment_defaults(workflow_id: str) -> dict:
    return server.workflow_segment_defaults(workflow_id)


def get_widget_metadata(workflow_id: str) -> dict:
    return server.workflow_widget_metadata(workflow_id)
