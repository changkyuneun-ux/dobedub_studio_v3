"""cleanup legacy category coupling

Revision ID: 20260810_0013
Revises: 20260810_0012
Create Date: 2026-08-10

B-06 step 4 (정리). This migration does NOT drop prompt_terms/prompt_categories
themselves - TASKS.md explicitly allows deferring that to a separate release
("별도 릴리스로 미루어도 무방"), and this app still needs *somewhere* to store
new keyword content (label/prompt text/etc.) since prompt_subcategory_keywords
has no content columns of its own. What it does remove is the structural
coupling that step 3's discrepancy report flagged: prompt_terms.category_id
was a NOT NULL FK to prompt_categories.id, which meant a brand-new
PromptSubcategory (one with no legacy_category_id, e.g. anything created via
POST /api/prompts/categories after step 3) could never receive new terms -
upsert_prompt_keyword() had to reject that case with a 400.

This migration:
  1. Relaxes prompt_terms.category_id to nullable (keeps the FK for any
     historical rows that still reference a real legacy category; new rows
     going forward are created with category_id = NULL).
  2. Drops prompt_subcategories.legacy_category_id - once (1) removes the
     reason upsert_prompt_keyword() needed it, nothing else reads it either
     (sync_prompt_catalog_hierarchy(), the lazy legacy<->new bridge, is
     removed from the service layer in this same step-4 commit).

Both alterations use batch mode because SQLite (the dev/test backend) cannot
alter a column's nullability or drop a column that carries a UNIQUE/FK
constraint via a plain ALTER TABLE - it has to rebuild the table. Batch mode
is a no-op passthrough on backends that support ALTER COLUMN/DROP COLUMN
directly (e.g. MySQL, see scripts/mysql_migration_smoke_check.py), so this
migration is safe on both.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260810_0013"
down_revision = "20260810_0012"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("prompt_terms") as batch_op:
        batch_op.alter_column("category_id", existing_type=sa.Integer(), nullable=True)

    with op.batch_alter_table("prompt_subcategories") as batch_op:
        batch_op.drop_column("legacy_category_id")


def downgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("prompt_subcategories") as batch_op:
        batch_op.add_column(sa.Column("legacy_category_id", sa.Integer(), nullable=True))
        batch_op.create_unique_constraint("uq_prompt_subcategories_legacy_category_id", ["legacy_category_id"])
        batch_op.create_foreign_key(
            "fk_prompt_subcategories_legacy_category_id_prompt_categories",
            "prompt_categories",
            ["legacy_category_id"],
            ["id"],
            ondelete="SET NULL",
        )

    # Backfill legacy_category_id the same way sync_prompt_catalog_hierarchy()
    # and the 0012 migration both did: match by code. This only recovers
    # subcategories that originated from a legacy category before step 4;
    # subcategories created after this migration went live have no legacy
    # counterpart and legitimately stay NULL on downgrade.
    bind.execute(sa.text(
        "update prompt_subcategories set legacy_category_id = ("
        "  select id from prompt_categories where prompt_categories.code = prompt_subcategories.code"
        ") where legacy_category_id is null"
    ))

    # Recover prompt_terms.category_id for rows that went NULL after step 4,
    # by following the term's active prompt_subcategory_keywords link back to
    # a subcategory that (as of the statement above) has a legacy_category_id.
    bind.execute(sa.text(
        "update prompt_terms set category_id = ("
        "  select ps.legacy_category_id"
        "  from prompt_subcategory_keywords psk"
        "  join prompt_subcategories ps on ps.id = psk.subcategory_id"
        "  where psk.keyword_id = prompt_terms.id and ps.legacy_category_id is not null"
        "  order by psk.subcategory_id limit 1"
        ") where category_id is null"
    ))

    remaining_null = bind.execute(sa.text(
        "select count(*) from prompt_terms where category_id is null"
    )).scalar()
    if remaining_null:
        # These are terms whose only subcategory link (if any) was itself
        # never connected to a legacy category - i.e. genuinely created after
        # step 4. There is no legacy category to point them at, so the old
        # NOT NULL invariant cannot be restored without deleting data. Leave
        # category_id nullable rather than raise; downgrading past step 4 on
        # a database that has taken step-4-era writes is a best-effort,
        # documented-lossy operation, not a hard failure.
        print(
            "[0013_cleanup_legacy_category_coupling] downgrade: "
            f"{remaining_null} prompt_terms row(s) have no legacy category to "
            "restore category_id from (created after step 4) - leaving "
            "prompt_terms.category_id nullable instead of restoring NOT NULL."
        )
        return

    with op.batch_alter_table("prompt_terms") as batch_op:
        batch_op.alter_column("category_id", existing_type=sa.Integer(), nullable=False)
