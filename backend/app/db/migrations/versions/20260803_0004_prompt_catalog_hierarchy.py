"""prompt catalog hierarchy

Revision ID: 20260803_0004
Revises: 20260803_0003
Create Date: 2026-08-03
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260803_0004"
down_revision = "20260803_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "prompt_scopes",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("name_ko", sa.String(length=191), nullable=False),
        sa.Column("name_en", sa.String(length=191), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_scopes")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_scopes_code")),
    )

    op.create_table(
        "prompt_category_groups",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("scope_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name_ko", sa.String(length=191), nullable=False),
        sa.Column("name_en", sa.String(length=191), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["scope_id"], ["prompt_scopes.id"], ondelete="CASCADE", name=op.f("fk_prompt_category_groups_scope_id_prompt_scopes")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_category_groups")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_category_groups_code")),
    )
    op.create_index(op.f("ix_prompt_category_groups_scope_id"), "prompt_category_groups", ["scope_id"], unique=False)

    op.create_table(
        "prompt_subcategories",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("category_group_id", sa.Integer(), nullable=False),
        sa.Column("legacy_category_id", sa.Integer(), nullable=True),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("scope_type", sa.String(length=32), nullable=False),
        sa.Column("selection_type", sa.String(length=32), nullable=False),
        sa.Column("required_yn", sa.Boolean(), nullable=False),
        sa.Column("max_select_count", sa.Integer(), nullable=True),
        sa.Column("name_ko", sa.String(length=191), nullable=False),
        sa.Column("name_en", sa.String(length=191), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["category_group_id"], ["prompt_category_groups.id"], ondelete="CASCADE", name=op.f("fk_prompt_subcategories_category_group_id_prompt_category_groups")),
        sa.ForeignKeyConstraint(["legacy_category_id"], ["prompt_categories.id"], ondelete="SET NULL", name=op.f("fk_prompt_subcategories_legacy_category_id_prompt_categories")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_prompt_subcategories")),
        sa.UniqueConstraint("code", name=op.f("uq_prompt_subcategories_code")),
        sa.UniqueConstraint("legacy_category_id", name=op.f("uq_prompt_subcategories_legacy_category_id")),
    )
    op.create_index(op.f("ix_prompt_subcategories_category_group_id"), "prompt_subcategories", ["category_group_id"], unique=False)

    op.create_table(
        "prompt_subcategory_keywords",
        sa.Column("subcategory_id", sa.Integer(), nullable=False),
        sa.Column("keyword_id", sa.Integer(), nullable=False),
        sa.Column("default_polarity", sa.String(length=32), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False),
        sa.Column("active_yn", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["keyword_id"], ["prompt_terms.id"], ondelete="CASCADE", name=op.f("fk_prompt_subcategory_keywords_keyword_id_prompt_terms")),
        sa.ForeignKeyConstraint(["subcategory_id"], ["prompt_subcategories.id"], ondelete="CASCADE", name=op.f("fk_prompt_subcategory_keywords_subcategory_id_prompt_subcategories")),
        sa.PrimaryKeyConstraint("subcategory_id", "keyword_id", name=op.f("pk_prompt_subcategory_keywords")),
    )
    op.create_index("ix_prompt_subcategory_keywords_subcategory_order", "prompt_subcategory_keywords", ["subcategory_id", "sort_order"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_prompt_subcategory_keywords_subcategory_order", table_name="prompt_subcategory_keywords")
    op.drop_table("prompt_subcategory_keywords")
    op.drop_index(op.f("ix_prompt_subcategories_category_group_id"), table_name="prompt_subcategories")
    op.drop_table("prompt_subcategories")
    op.drop_index(op.f("ix_prompt_category_groups_scope_id"), table_name="prompt_category_groups")
    op.drop_table("prompt_category_groups")
    op.drop_table("prompt_scopes")
