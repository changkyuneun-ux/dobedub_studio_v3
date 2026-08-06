"""prompt builder schema

Revision ID: 20260802_0002
Revises: 20260802_0001
Create Date: 2026-08-02
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260802_0002"
down_revision = "20260802_0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_categories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("group_code", sa.String(length=64), nullable=False),
        sa.Column("name_ko", sa.String(length=191), nullable=False),
        sa.Column("name_en", sa.String(length=191), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_categories")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_categories_code")),
    )
    op.create_index(op.f("ix_prompt_categories_group_code"), "prompt_categories", ["group_code"], unique=False)

    op.create_table(
        "prompt_rules",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("rule_type", sa.String(length=64), nullable=False),
        sa.Column("condition_json", sa.JSON(), nullable=False),
        sa.Column("action_json", sa.JSON(), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_rules")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_rules_code")),
    )

    op.create_table(
        "prompt_templates",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("prompt_type", sa.String(length=32), nullable=False),
        sa.Column("template_text", sa.Text(), nullable=False),
        sa.Column("schema_json", sa.JSON(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_templates")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_templates_code")),
    )
    op.create_index(op.f("ix_prompt_templates_prompt_type"), "prompt_templates", ["prompt_type"], unique=False)

    op.create_table(
        "prompt_terms",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("label_ko", sa.String(length=191), nullable=False),
        sa.Column("label_en", sa.String(length=191), nullable=False),
        sa.Column("prompt_text", sa.Text(), nullable=False),
        sa.Column("negative_text", sa.Text(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["prompt_categories.id"], ondelete="CASCADE", name=op.f("fk_prompt_terms_category_id_prompt_categories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_terms")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_terms_code")),
    )
    op.create_index("ix_prompt_terms_category_order", "prompt_terms", ["category_id", "sort_order"], unique=False)

    op.create_table(
        "prompt_generation_requests",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("workflow_id", sa.String(length=191), nullable=True),
        sa.Column("segment_index", sa.Integer(), nullable=True),
        sa.Column("language", sa.String(length=16), nullable=False),
        sa.Column("scene_json", sa.JSON(), nullable=False),
        sa.Column("constraints_json", sa.JSON(), nullable=False),
        sa.Column("selected_term_ids", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=64), nullable=False),
        sa.Column("created_by", sa.String(length=191), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_prompt_generation_requests_created_by_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_generation_requests")),
    )
    op.create_index(op.f("ix_prompt_generation_requests_status"), "prompt_generation_requests", ["status"], unique=False)
    op.create_index("ix_prompt_generation_requests_workflow_segment", "prompt_generation_requests", ["workflow_id", "segment_index"], unique=False)
    op.create_index(op.f("ix_prompt_generation_requests_workflow_id"), "prompt_generation_requests", ["workflow_id"], unique=False)

    op.create_table(
        "prompt_term_relations",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("source_term_id", sa.Integer(), nullable=False),
        sa.Column("target_term_id", sa.Integer(), nullable=False),
        sa.Column("relation_type", sa.String(length=64), nullable=False),
        sa.Column("weight", sa.Float(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_term_id"], ["prompt_terms.id"], ondelete="CASCADE", name=op.f("fk_prompt_term_relations_source_term_id_prompt_terms")),
        sa.ForeignKeyConstraint(["target_term_id"], ["prompt_terms.id"], ondelete="CASCADE", name=op.f("fk_prompt_term_relations_target_term_id_prompt_terms")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_term_relations")),
    )
    op.create_index("ix_prompt_term_relations_source_type", "prompt_term_relations", ["source_term_id", "relation_type"], unique=False)

    op.create_table(
        "prompt_generation_outputs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("request_id", sa.String(length=64), nullable=False),
        sa.Column("provider", sa.String(length=64), nullable=False),
        sa.Column("positive_prompt", sa.Text(), nullable=False),
        sa.Column("negative_prompt", sa.Text(), nullable=False),
        sa.Column("used_term_ids", sa.JSON(), nullable=False),
        sa.Column("added_term_ids", sa.JSON(), nullable=False),
        sa.Column("warnings_json", sa.JSON(), nullable=False),
        sa.Column("raw_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["request_id"], ["prompt_generation_requests.id"], ondelete="CASCADE", name=op.f("fk_prompt_generation_outputs_request_id_prompt_generation_requests")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_generation_outputs")),
    )

    op.create_table(
        "prompt_feedback",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("output_id", sa.String(length=64), nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=True),
        sa.Column("rating", sa.Integer(), nullable=True),
        sa.Column("edited_positive_prompt", sa.Text(), nullable=True),
        sa.Column("edited_negative_prompt", sa.Text(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(length=191), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], name=op.f("fk_prompt_feedback_created_by_users")),
        sa.ForeignKeyConstraint(["output_id"], ["prompt_generation_outputs.id"], ondelete="CASCADE", name=op.f("fk_prompt_feedback_output_id_prompt_generation_outputs")),
        sa.ForeignKeyConstraint(["task_id"], ["workflow_tasks.id"], name=op.f("fk_prompt_feedback_task_id_workflow_tasks")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_feedback")),
    )


def downgrade() -> None:
    op.drop_table("prompt_feedback")
    op.drop_table("prompt_generation_outputs")
    op.drop_index("ix_prompt_term_relations_source_type", table_name="prompt_term_relations")
    op.drop_table("prompt_term_relations")
    op.drop_index(op.f("ix_prompt_generation_requests_workflow_id"), table_name="prompt_generation_requests")
    op.drop_index("ix_prompt_generation_requests_workflow_segment", table_name="prompt_generation_requests")
    op.drop_index(op.f("ix_prompt_generation_requests_status"), table_name="prompt_generation_requests")
    op.drop_table("prompt_generation_requests")
    op.drop_index("ix_prompt_terms_category_order", table_name="prompt_terms")
    op.drop_table("prompt_terms")
    op.drop_index(op.f("ix_prompt_templates_prompt_type"), table_name="prompt_templates")
    op.drop_table("prompt_templates")
    op.drop_table("prompt_rules")
    op.drop_index(op.f("ix_prompt_categories_group_code"), table_name="prompt_categories")
    op.drop_table("prompt_categories")
