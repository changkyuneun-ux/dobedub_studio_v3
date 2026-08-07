"""sandbox pod permissions

Revision ID: 20260807_0011
Revises: 20260806_0010
Create Date: 2026-08-07
"""
from __future__ import annotations

from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "20260807_0011"
down_revision = "20260806_0010"
branch_labels = None
depends_on = None


PERMISSIONS = [
    ("sandbox:read", "sandbox", "read", "Sandbox Pod 조회", "전용 RunPod Sandbox Pod 상태와 HTTP 서비스 조회", 120),
    ("sandbox:control", "sandbox", "control", "Sandbox Pod 제어", "전용 RunPod Sandbox Pod 시작 및 중지", 121),
]


def upgrade() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    permission_table = sa.table(
        "permissions",
        sa.column("code", sa.String()),
        sa.column("domain", sa.String()),
        sa.column("action", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    existing = {row[0] for row in bind.execute(sa.text("select code from permissions")).all()}
    rows = [
        {
            "code": code,
            "domain": domain,
            "action": action,
            "name": name,
            "description": description,
            "is_system": True,
            "is_active": True,
            "sort_order": sort_order,
            "created_at": now,
            "updated_at": now,
        }
        for code, domain, action, name, description, sort_order in PERMISSIONS
        if code not in existing
    ]
    if rows:
        op.bulk_insert(permission_table, rows)


def downgrade() -> None:
    codes = tuple(code for code, *_ in PERMISSIONS)
    op.get_bind().execute(
        sa.text("delete from permissions where code in :codes").bindparams(sa.bindparam("codes", expanding=True)),
        {"codes": codes},
    )
