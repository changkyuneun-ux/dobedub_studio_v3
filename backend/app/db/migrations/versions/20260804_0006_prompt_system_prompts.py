"""prompt system prompts

Revision ID: 20260804_0006
Revises: 20260803_0005
Create Date: 2026-08-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260804_0006"
down_revision = "20260803_0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_system_prompts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("model_family", sa.String(length=64), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_system_prompts")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_system_prompts_code")),
    )


def downgrade() -> None:
    op.drop_table("prompt_system_prompts")
