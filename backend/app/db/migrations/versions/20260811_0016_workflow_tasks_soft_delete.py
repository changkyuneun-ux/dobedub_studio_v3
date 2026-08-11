"""workflow_tasks soft delete

Revision ID: 20260811_0016
Revises: 20260811_0015
Create Date: 2026-08-11

B-05: 이력 삭제를 하드 삭제에서 soft delete로 전환한다. workflow_tasks.deleted_at을
추가하고, NULL이 아니면 이력 목록·총계·재사용 프롬프트 조회에서 제외한다. 삭제
행위는 A-04 감사 로그(action="history.delete")에 이미 기록된다. 결과물 파일(assets)은
삭제하지 않고 남긴다.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260811_0016"
down_revision = "20260811_0015"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("workflow_tasks", sa.Column("deleted_at", sa.DateTime(), nullable=True))
    op.create_index("ix_workflow_tasks_deleted_at", "workflow_tasks", ["deleted_at"])


def downgrade() -> None:
    op.drop_index("ix_workflow_tasks_deleted_at", table_name="workflow_tasks")
    op.drop_column("workflow_tasks", "deleted_at")
