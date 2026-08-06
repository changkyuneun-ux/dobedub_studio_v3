"""task prompt review fields

Revision ID: 20260804_0008
Revises: 20260804_0007
Create Date: 2026-08-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260804_0008"
down_revision = "20260804_0007"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("task_prompts", sa.Column("reuse_eligible", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("task_prompts", sa.Column("review_status", sa.String(length=32), nullable=False, server_default="unreviewed"))
    op.add_column("task_prompts", sa.Column("review_flags_json", sa.JSON(), nullable=True))
    op.add_column("task_prompts", sa.Column("reviewed_by", sa.String(length=191), nullable=True))
    op.add_column("task_prompts", sa.Column("reviewed_at", sa.DateTime(), nullable=True))
    op.create_index(op.f("ix_task_prompts_review_status"), "task_prompts", ["review_status"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_task_prompts_review_status"), table_name="task_prompts")
    op.drop_column("task_prompts", "reviewed_at")
    op.drop_column("task_prompts", "reviewed_by")
    op.drop_column("task_prompts", "review_flags_json")
    op.drop_column("task_prompts", "review_status")
    op.drop_column("task_prompts", "reuse_eligible")
