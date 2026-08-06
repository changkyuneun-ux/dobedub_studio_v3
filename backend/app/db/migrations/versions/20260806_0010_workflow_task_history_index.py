"""workflow task history index

Revision ID: 20260806_0010
Revises: 20260805_0009
Create Date: 2026-08-06
"""
from __future__ import annotations

from alembic import op


revision = "20260806_0010"
down_revision = "20260805_0009"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_workflow_tasks_created_at_id", "workflow_tasks", ["created_at", "id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_workflow_tasks_created_at_id", table_name="workflow_tasks")
