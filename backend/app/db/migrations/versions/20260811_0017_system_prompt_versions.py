"""system prompt versions

Revision ID: 20260811_0017
Revises: 20260811_0016
Create Date: 2026-08-11

B-08: 시스템 지시문(prompt_system_prompts) 버전 이력. 저장할 때마다 새 상태를 한
행으로 스냅샷해 7a에서 이전 버전으로 되돌릴 수 있게 한다. created_by는 audit_logs와
같은 이유로 users.id에 FK를 걸지 않는다(느슨한 참조).
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260811_0017"
down_revision = "20260811_0016"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_system_prompt_versions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False, server_default="runpod_vllm"),
        sa.Column("model_family", sa.String(length=64), nullable=False, server_default="qwen"),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("created_by", sa.String(length=191), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_prompt_system_prompt_versions_code", "prompt_system_prompt_versions", ["code"])
    op.create_index("ix_prompt_system_prompt_versions_code_created", "prompt_system_prompt_versions", ["code", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_prompt_system_prompt_versions_code_created", table_name="prompt_system_prompt_versions")
    op.drop_index("ix_prompt_system_prompt_versions_code", table_name="prompt_system_prompt_versions")
    op.drop_table("prompt_system_prompt_versions")
