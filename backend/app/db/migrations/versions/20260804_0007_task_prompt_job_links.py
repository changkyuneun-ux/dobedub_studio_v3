"""task prompt job links

Revision ID: 20260804_0007
Revises: 20260804_0006
Create Date: 2026-08-04
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260804_0007"
down_revision = "20260804_0006"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "task_prompts",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=191), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=False),
        sa.Column("model_profile_id", sa.Integer(), nullable=True),
        sa.Column("model_name", sa.String(length=191), nullable=True),
        sa.Column("prompt_generation_output_id", sa.String(length=64), nullable=True),
        sa.Column("positive_prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=False),
        sa.Column("input_asset_ids", sa.JSON(), nullable=False),
        sa.Column("output_asset_ids", sa.JSON(), nullable=False),
        sa.Column("quality_rating", sa.Integer(), nullable=True),
        sa.Column("quality_comment", sa.Text(), nullable=True),
        sa.Column("reuse_count", sa.Integer(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], name=op.f("fk_task_prompts_model_profile_id_model_profiles")),
        sa.ForeignKeyConstraint(["prompt_generation_output_id"], ["prompt_generation_outputs.id"], name=op.f("fk_task_prompts_prompt_generation_output_id_prompt_generation_outputs")),
        sa.ForeignKeyConstraint(["task_id"], ["workflow_tasks.id"], ondelete="CASCADE", name=op.f("fk_task_prompts_task_id_workflow_tasks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_prompts")),
    )
    op.create_index(op.f("ix_task_prompts_task_id"), "task_prompts", ["task_id"], unique=False)
    op.create_index(op.f("ix_task_prompts_workflow_id"), "task_prompts", ["workflow_id"], unique=False)
    op.create_index("ix_task_prompts_task_segment", "task_prompts", ["task_id", "segment_index"], unique=False)
    op.create_index("ix_task_prompts_workflow_segment", "task_prompts", ["workflow_id", "segment_index"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_prompts_workflow_segment", table_name="task_prompts")
    op.drop_index("ix_task_prompts_task_segment", table_name="task_prompts")
    op.drop_index(op.f("ix_task_prompts_workflow_id"), table_name="task_prompts")
    op.drop_index(op.f("ix_task_prompts_task_id"), table_name="task_prompts")
    op.drop_table("task_prompts")
