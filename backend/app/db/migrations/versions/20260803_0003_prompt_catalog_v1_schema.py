"""prompt catalog v1 schema

Revision ID: 20260803_0003
Revises: 20260802_0002
Create Date: 2026-08-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260803_0003"
down_revision = "20260802_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("prompt_categories", sa.Column("parent_category_id", sa.Integer(), nullable=True))
    op.add_column("prompt_categories", sa.Column("scope_type", sa.String(length=32), server_default="SCENE", nullable=False))
    op.add_column("prompt_categories", sa.Column("selection_type", sa.String(length=32), server_default="MULTIPLE", nullable=False))
    op.add_column("prompt_categories", sa.Column("required_yn", sa.Boolean(), server_default=sa.false(), nullable=False))
    op.add_column("prompt_categories", sa.Column("max_select_count", sa.Integer(), nullable=True))

    op.add_column("prompt_terms", sa.Column("canonical_key", sa.String(length=191), nullable=True))
    op.add_column("prompt_terms", sa.Column("description", sa.Text(), nullable=True))
    op.add_column("prompt_terms", sa.Column("risk_level", sa.String(length=32), server_default="NONE", nullable=False))
    op.create_index(op.f("ix_prompt_terms_canonical_key"), "prompt_terms", ["canonical_key"], unique=False)

    op.create_table(
        "prompt_category_terms",
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("default_polarity", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active_yn", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["category_id"], ["prompt_categories.id"], ondelete="CASCADE", name=op.f("fk_prompt_category_terms_category_id_prompt_categories")),
        sa.ForeignKeyConstraint(["term_id"], ["prompt_terms.id"], ondelete="CASCADE", name=op.f("fk_prompt_category_terms_term_id_prompt_terms")),
        sa.PrimaryKeyConstraint("category_id", "term_id", name=op.f("pk_prompt_category_terms")),
    )
    op.create_index("ix_prompt_category_terms_category_order", "prompt_category_terms", ["category_id", "sort_order"], unique=False)

    op.create_table(
        "model_profiles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("model_family", sa.String(length=64), nullable=False),
        sa.Column("model_name", sa.String(length=191), nullable=False),
        sa.Column("model_version", sa.String(length=64), nullable=True),
        sa.Column("task_type", sa.String(length=64), nullable=False),
        sa.Column("prompt_language", sa.String(length=16), nullable=False),
        sa.Column("supports_negative_prompt", sa.Boolean(), nullable=False),
        sa.Column("supports_prompt_weight", sa.Boolean(), nullable=False),
        sa.Column("capabilities_json", sa.JSON(), nullable=False),
        sa.Column("default_parameters_json", sa.JSON(), nullable=False),
        sa.Column("active_yn", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_model_profiles")),
    )
    op.create_index(op.f("ix_model_profiles_model_family"), "model_profiles", ["model_family"], unique=False)

    op.create_table(
        "prompt_term_renderings",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("term_id", sa.Integer(), nullable=False),
        sa.Column("model_profile_id", sa.Integer(), nullable=True),
        sa.Column("language_code", sa.String(length=16), nullable=False),
        sa.Column("polarity", sa.String(length=32), nullable=False),
        sa.Column("render_text", sa.Text(), nullable=False),
        sa.Column("render_version", sa.String(length=32), nullable=False),
        sa.Column("active_yn", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["model_profile_id"], ["model_profiles.id"], ondelete="CASCADE", name=op.f("fk_prompt_term_renderings_model_profile_id_model_profiles")),
        sa.ForeignKeyConstraint(["term_id"], ["prompt_terms.id"], ondelete="CASCADE", name=op.f("fk_prompt_term_renderings_term_id_prompt_terms")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_term_renderings")),
    )
    op.create_index("ix_prompt_term_renderings_lookup", "prompt_term_renderings", ["term_id", "model_profile_id", "polarity"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_prompt_term_renderings_lookup", table_name="prompt_term_renderings")
    op.drop_table("prompt_term_renderings")
    op.drop_index(op.f("ix_model_profiles_model_family"), table_name="model_profiles")
    op.drop_table("model_profiles")
    op.drop_index("ix_prompt_category_terms_category_order", table_name="prompt_category_terms")
    op.drop_table("prompt_category_terms")
    op.drop_index(op.f("ix_prompt_terms_canonical_key"), table_name="prompt_terms")
    op.drop_column("prompt_terms", "risk_level")
    op.drop_column("prompt_terms", "description")
    op.drop_column("prompt_terms", "canonical_key")
    op.drop_column("prompt_categories", "max_select_count")
    op.drop_column("prompt_categories", "required_yn")
    op.drop_column("prompt_categories", "selection_type")
    op.drop_column("prompt_categories", "scope_type")
    op.drop_column("prompt_categories", "parent_category_id")
