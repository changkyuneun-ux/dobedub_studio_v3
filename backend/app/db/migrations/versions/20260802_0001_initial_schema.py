"""initial dobedub studio schema

Revision ID: 20260802_0001
Revises:
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260802_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=191), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("email", sa.String(length=191), nullable=True),
        sa.Column("role", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
    )
    op.create_index(op.f("ix_users_email"), "users", ["email"], unique=False)

    op.create_table(
        "assets",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("asset_type", sa.String(length=64), nullable=False),
        sa.Column("file_name", sa.String(length=512), nullable=False),
        sa.Column("mime_type", sa.String(length=191), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("public_url", sa.String(length=2048), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_assets")),
    )
    op.create_index(op.f("ix_assets_asset_type"), "assets", ["asset_type"], unique=False)

    op.create_table(
        "workflow_tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("runpod_job_id", sa.String(length=191), nullable=True),
        sa.Column("workflow_id", sa.String(length=191), nullable=False),
        sa.Column("execution_mode", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("progress", sa.Integer(), nullable=False),
        sa.Column("worker_name", sa.String(length=191), nullable=True),
        sa.Column("user_id", sa.String(length=191), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("elapsed_seconds", sa.Integer(), nullable=True),
        sa.Column("positive_prompts", sa.JSON(), nullable=False),
        sa.Column("negative_prompts", sa.JSON(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=False),
        sa.Column("wan_node_config", sa.JSON(), nullable=False),
        sa.Column("patch_summary", sa.JSON(), nullable=False),
        sa.Column("payload_json", sa.JSON(), nullable=False),
        sa.Column("runpod_submit_json", sa.JSON(), nullable=False),
        sa.Column("runpod_status_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_workflow_tasks_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workflow_tasks")),
    )
    op.create_index(op.f("ix_workflow_tasks_runpod_job_id"), "workflow_tasks", ["runpod_job_id"], unique=False)
    op.create_index(op.f("ix_workflow_tasks_status"), "workflow_tasks", ["status"], unique=False)
    op.create_index(op.f("ix_workflow_tasks_workflow_id"), "workflow_tasks", ["workflow_id"], unique=False)

    op.create_table(
        "config_snapshots",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=191), nullable=False),
        sa.Column("name", sa.String(length=512), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("user_id", sa.String(length=191), nullable=True),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_config_snapshots_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_config_snapshots")),
    )
    op.create_index(op.f("ix_config_snapshots_workflow_id"), "config_snapshots", ["workflow_id"], unique=False)

    op.create_table(
        "prompt_entries",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=191), nullable=True),
        sa.Column("segment_index", sa.Integer(), nullable=True),
        sa.Column("prompt_type", sa.String(length=32), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=191), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_prompt_entries_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_entries")),
    )
    op.create_index(op.f("ix_prompt_entries_prompt_type"), "prompt_entries", ["prompt_type"], unique=False)
    op.create_index(op.f("ix_prompt_entries_workflow_id"), "prompt_entries", ["workflow_id"], unique=False)

    op.create_table(
        "reports",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("title", sa.String(length=512), nullable=False),
        sa.Column("storage_backend", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=1024), nullable=False),
        sa.Column("markdown", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["workflow_tasks.id"], name=op.f("fk_reports_task_id_workflow_tasks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_reports")),
    )

    op.create_table(
        "task_input_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("slot_index", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name=op.f("fk_task_input_assets_asset_id_assets")),
        sa.ForeignKeyConstraint(["task_id"], ["workflow_tasks.id"], ondelete="CASCADE", name=op.f("fk_task_input_assets_task_id_workflow_tasks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_input_assets")),
    )
    op.create_index("ix_task_input_assets_task_slot", "task_input_assets", ["task_id", "slot_index"], unique=False)

    op.create_table(
        "task_output_assets",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("asset_id", sa.String(length=64), nullable=False),
        sa.Column("output_role", sa.String(length=32), nullable=False),
        sa.Column("segment_index", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["asset_id"], ["assets.id"], name=op.f("fk_task_output_assets_asset_id_assets")),
        sa.ForeignKeyConstraint(["task_id"], ["workflow_tasks.id"], ondelete="CASCADE", name=op.f("fk_task_output_assets_task_id_workflow_tasks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task_output_assets")),
    )
    op.create_index("ix_task_output_assets_task_role", "task_output_assets", ["task_id", "output_role", "segment_index"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_output_assets_task_role", table_name="task_output_assets")
    op.drop_table("task_output_assets")
    op.drop_index("ix_task_input_assets_task_slot", table_name="task_input_assets")
    op.drop_table("task_input_assets")
    op.drop_table("reports")
    op.drop_index(op.f("ix_prompt_entries_workflow_id"), table_name="prompt_entries")
    op.drop_index(op.f("ix_prompt_entries_prompt_type"), table_name="prompt_entries")
    op.drop_table("prompt_entries")
    op.drop_index(op.f("ix_config_snapshots_workflow_id"), table_name="config_snapshots")
    op.drop_table("config_snapshots")
    op.drop_index(op.f("ix_workflow_tasks_workflow_id"), table_name="workflow_tasks")
    op.drop_index(op.f("ix_workflow_tasks_status"), table_name="workflow_tasks")
    op.drop_index(op.f("ix_workflow_tasks_runpod_job_id"), table_name="workflow_tasks")
    op.drop_table("workflow_tasks")
    op.drop_index(op.f("ix_assets_asset_type"), table_name="assets")
    op.drop_table("assets")
    op.drop_index(op.f("ix_users_email"), table_name="users")
    op.drop_table("users")
