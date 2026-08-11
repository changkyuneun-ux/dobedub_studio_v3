"""collections

Revision ID: 20260811_0015
Revises: 20260811_0014
Create Date: 2026-08-11

A-02: 자산(assets)을 묶는 사용자 컬렉션. 화면 5c(자산 · 컬렉션)가 요구한다.
- collections: 컬렉션 자체(이름·생성자·생성시각)
- collection_items: 컬렉션 ↔ 자산 연결(컬렉션당 자산은 1회, 정렬 순서 보관)

created_by는 audit_logs.actor_id와 같은 이유로 users.id에 FK를 걸지 않는다(느슨한
참조 - 생성자가 이후 삭제돼도 컬렉션은 남는다). collection_items는 (collection_id,
asset_id) 복합 PK로 중복 담기를 막고, collections/assets 삭제 시 CASCADE로 함께 정리.
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260811_0015"
down_revision = "20260811_0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "collections",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("created_by", sa.String(length=191), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_collections_created_by", "collections", ["created_by"])
    op.create_index("ix_collections_created_at_id", "collections", ["created_at", "id"])

    op.create_table(
        "collection_items",
        sa.Column(
            "collection_id",
            sa.Integer(),
            sa.ForeignKey("collections.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "asset_id",
            sa.String(length=64),
            sa.ForeignKey("assets.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )
    op.create_index(
        "ix_collection_items_collection_order",
        "collection_items",
        ["collection_id", "sort_order"],
    )


def downgrade() -> None:
    op.drop_index("ix_collection_items_collection_order", table_name="collection_items")
    op.drop_table("collection_items")
    op.drop_index("ix_collections_created_at_id", table_name="collections")
    op.drop_index("ix_collections_created_by", table_name="collections")
    op.drop_table("collections")
