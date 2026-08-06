"""rbac feature permissions

Revision ID: 20260805_0009
Revises: 20260804_0008
Create Date: 2026-08-05
"""
from __future__ import annotations

import json
from datetime import datetime

from alembic import op
import sqlalchemy as sa


revision = "20260805_0009"
down_revision = "20260804_0008"
branch_labels = None
depends_on = None


ROLES = [
    {"code": "SUPER_ADMIN", "name": "Super Admin", "description": "전체 운영 및 시스템 설정 권한", "level": 40, "sort_order": 10},
    {"code": "ADMIN", "name": "Admin", "description": "사용자, 워크플로우, Prompt Catalog 운영 관리 권한", "level": 30, "sort_order": 20},
    {"code": "OPERATOR", "name": "Operator", "description": "영상 생성, 작업 조회, 프롬프트 리뷰 등 실무 작업 권한", "level": 20, "sort_order": 30},
    {"code": "VIEWER", "name": "Viewer", "description": "작업과 결과 조회 중심의 읽기 전용 권한", "level": 10, "sort_order": 40},
]


PERMISSIONS = [
    ("admin:*", "admin", "*", "Admin 전체", "관리자 기능 전체 접근", 10),
    ("users:read", "users", "read", "사용자 조회", "사용자 목록과 상세 조회", 20),
    ("users:write", "users", "write", "사용자 수정", "사용자 등록, 수정, 상태 변경", 21),
    ("roles:read", "roles", "read", "역할/권한 조회", "역할과 권한 그룹 조회", 30),
    ("roles:write", "roles", "write", "역할/권한 수정", "역할별 권한 구성 변경", 31),
    ("workflows:read", "workflows", "read", "워크플로우 조회", "워크플로우 목록과 메타데이터 조회", 40),
    ("workflows:write", "workflows", "write", "워크플로우 수정", "워크플로우 등록과 수정", 41),
    ("workflows:activate", "workflows", "activate", "워크플로우 활성화", "워크플로우 활성화와 비활성화", 42),
    ("prompt-catalog:read", "prompt-catalog", "read", "카탈로그 조회", "Prompt Catalog 조회", 50),
    ("prompt-catalog:write", "prompt-catalog", "write", "카탈로그 수정", "카테고리, 서브 카테고리, 키워드 관리", 51),
    ("prompts:build", "prompts", "build", "프롬프트 생성", "Prompt Builder와 Qwen 프롬프트 생성", 60),
    ("prompts:reuse", "prompts", "reuse", "프롬프트 재사용", "재사용 가능 프롬프트 검색과 적용", 61),
    ("prompts:review", "prompts", "review", "프롬프트 리뷰", "품질 등급, 코멘트, 재사용 가능 여부 관리", 62),
    ("jobs:run", "jobs", "run", "작업 실행", "영상 생성 작업 제출", 70),
    ("jobs:cancel", "jobs", "cancel", "작업 취소", "RunPod 생성 작업 취소", 71),
    ("history:read", "history", "read", "작업 이력 조회", "작업 결과와 이력 조회", 80),
    ("history:delete", "history", "delete", "작업 이력 삭제", "작업과 관련 asset 삭제", 81),
    ("metadata:read", "metadata", "read", "메타데이터 조회", "Workflow metadata 조회", 90),
    ("metadata:rebuild", "metadata", "rebuild", "메타데이터 재생성", "Workflow metadata rebuild", 91),
    ("system:read", "system", "read", "시스템 상태 조회", "ComfyUI/Qwen/DB 상태 확인", 100),
    ("manual:read", "manual", "read", "사용자 매뉴얼 조회", "사용자 매뉴얼 조회", 110),
]


ROLE_PERMISSION_CODES = {
    "SUPER_ADMIN": ["admin:*"],
    "ADMIN": [
        "users:read",
        "users:write",
        "roles:read",
        "roles:write",
        "workflows:read",
        "workflows:write",
        "workflows:activate",
        "prompt-catalog:read",
        "prompt-catalog:write",
        "prompts:review",
        "history:read",
        "history:delete",
        "metadata:read",
        "metadata:rebuild",
        "system:read",
        "manual:read",
    ],
    "OPERATOR": [
        "workflows:read",
        "jobs:run",
        "jobs:cancel",
        "history:read",
        "prompts:build",
        "prompts:reuse",
        "prompts:review",
        "metadata:read",
        "system:read",
        "manual:read",
    ],
    "VIEWER": [
        "workflows:read",
        "history:read",
        "metadata:read",
        "system:read",
        "manual:read",
    ],
}


RESOURCES = [
    ("MENU", "top.history", "History/Saved Videos", "history:read", "/studio/history", None, 10),
    ("MENU", "top.status", "Check Status", "system:read", "/studio/status", None, 20),
    ("MENU", "top.metadata", "Metadata View", "metadata:read", "/studio/metadata", None, 30),
    ("MENU", "top.manual", "User Manual", "manual:read", "/studio/manual", None, 40),
    ("MENU", "top.admin.users", "Admin > Users", "users:read", "/studio/admin", None, 51),
    ("MENU", "top.admin.roles", "Admin > Permission Catalog", "roles:read", "/studio/admin", None, 52),
    ("MENU", "top.admin.workflows", "Admin > Workflows", "workflows:write", "/studio/admin", None, 53),
    ("MENU", "top.admin.catalog", "Admin > Prompt Catalog", "prompt-catalog:write", "/studio/admin", None, 54),
    ("ACTION", "action.metadata_rebuild", "Rebuild Metadata", "metadata:rebuild", None, None, 100),
    ("ACTION", "action.admin_user_save", "Save User", "users:write", None, None, 110),
    ("ACTION", "action.admin_role_save", "Save Role Permissions", "roles:write", None, None, 120),
    ("ACTION", "action.workflow_save", "Save Workflow", "workflows:write", None, None, 130),
    ("ACTION", "action.workflow_activate", "Activate Workflow", "workflows:activate", None, None, 140),
    ("ACTION", "action.catalog_save", "Save Prompt Catalog", "prompt-catalog:write", None, None, 150),
    ("ACTION", "action.prompt_builder", "Prompt Builder", "prompts:build", None, None, 160),
    ("ACTION", "action.prompt_reuse", "Prompt Reuse", "prompts:reuse", None, None, 170),
    ("ACTION", "action.prompt_review_save", "Save Prompt Review", "prompts:review", None, None, 180),
    ("ACTION", "action.generate_video", "Generate Video", "jobs:run", None, None, 190),
    ("ACTION", "action.cancel_generation", "Cancel Generation", "jobs:cancel", None, None, 200),
    ("ACTION", "action.history_delete", "Delete History", "history:delete", None, None, 210),
    ("API", "api.admin.users", "Admin Users API", "users:read", "/api/admin/users", "GET", 300),
    ("API", "api.admin.users_write", "Admin User Write API", "users:write", "/api/admin/users", "POST/PUT", 301),
    ("API", "api.admin.roles", "Admin Roles API", "roles:read", "/api/admin/permissions", "GET", 310),
    ("API", "api.admin.workflows", "Admin Workflows API", "workflows:read", "/api/admin/workflows", "GET", 320),
    ("API", "api.jobs", "Jobs API", "jobs:run", "/api/jobs", "POST", 330),
    ("API", "api.jobs_cancel", "Job Cancel API", "jobs:cancel", "/api/jobs/{task_id}/cancel", "POST", 331),
    ("API", "api.history", "History API", "history:read", "/api/history", "GET", 340),
    ("API", "api.history_delete", "History Delete API", "history:delete", "/api/history/{task_id}/delete", "POST", 341),
    ("API", "api.metadata", "Metadata API", "metadata:read", "/api/metadata", "GET", 350),
    ("API", "api.metadata_rebuild", "Metadata Rebuild API", "metadata:rebuild", "/api/metadata/rebuild", "POST", 351),
    ("API", "api.prompts", "Prompt Builder API", "prompts:build", "/api/prompts", "POST", 360),
    ("API", "api.prompt_reuse", "Reusable Prompt API", "prompts:reuse", "/api/prompts/reusable", "GET", 361),
]


def upgrade() -> None:
    op.create_table(
        "roles",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("level", sa.Integer(), nullable=False, server_default="10"),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_roles")),
        sa.UniqueConstraint("code", name=op.f("uq_roles_code")),
    )
    op.create_table(
        "permissions",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=128), nullable=False),
        sa.Column("domain", sa.String(length=64), nullable=False),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=191), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_system", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_permissions")),
        sa.UniqueConstraint("code", name=op.f("uq_permissions_code")),
    )
    op.create_index(op.f("ix_permissions_domain"), "permissions", ["domain"], unique=False)
    op.create_index(op.f("ix_permissions_action"), "permissions", ["action"], unique=False)
    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.Integer(), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE", name=op.f("fk_role_permissions_permission_id_permissions")),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE", name=op.f("fk_role_permissions_role_id_roles")),
        sa.PrimaryKeyConstraint("role_id", "permission_id", name=op.f("pk_role_permissions")),
    )
    op.create_table(
        "user_permissions",
        sa.Column("user_id", sa.String(length=191), nullable=False),
        sa.Column("permission_id", sa.Integer(), nullable=False),
        sa.Column("grant_type", sa.String(length=16), nullable=False, server_default="ALLOW"),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE", name=op.f("fk_user_permissions_permission_id_permissions")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE", name=op.f("fk_user_permissions_user_id_users")),
        sa.PrimaryKeyConstraint("user_id", "permission_id", name=op.f("pk_user_permissions")),
    )
    op.create_table(
        "ui_permission_resources",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("resource_type", sa.String(length=32), nullable=False),
        sa.Column("resource_key", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=191), nullable=False),
        sa.Column("required_permission_code", sa.String(length=128), nullable=False),
        sa.Column("route_path", sa.String(length=512), nullable=True),
        sa.Column("method", sa.String(length=16), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="100"),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_ui_permission_resources")),
        sa.UniqueConstraint("resource_key", name=op.f("uq_ui_permission_resources_resource_key")),
    )
    op.create_index(op.f("ix_ui_permission_resources_resource_type"), "ui_permission_resources", ["resource_type"], unique=False)
    op.create_index(op.f("ix_ui_permission_resources_required_permission_code"), "ui_permission_resources", ["required_permission_code"], unique=False)

    seed_rbac()


def downgrade() -> None:
    op.drop_index(op.f("ix_ui_permission_resources_required_permission_code"), table_name="ui_permission_resources")
    op.drop_index(op.f("ix_ui_permission_resources_resource_type"), table_name="ui_permission_resources")
    op.drop_table("ui_permission_resources")
    op.drop_table("user_permissions")
    op.drop_table("role_permissions")
    op.drop_index(op.f("ix_permissions_action"), table_name="permissions")
    op.drop_index(op.f("ix_permissions_domain"), table_name="permissions")
    op.drop_table("permissions")
    op.drop_table("roles")


def seed_rbac() -> None:
    bind = op.get_bind()
    now = datetime.utcnow()
    role_table = sa.table(
        "roles",
        sa.column("id", sa.Integer()),
        sa.column("code", sa.String()),
        sa.column("name", sa.String()),
        sa.column("description", sa.Text()),
        sa.column("level", sa.Integer()),
        sa.column("is_system", sa.Boolean()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    permission_table = sa.table(
        "permissions",
        sa.column("id", sa.Integer()),
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
    role_permission_table = sa.table(
        "role_permissions",
        sa.column("role_id", sa.Integer()),
        sa.column("permission_id", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
    )
    user_permission_table = sa.table(
        "user_permissions",
        sa.column("user_id", sa.String()),
        sa.column("permission_id", sa.Integer()),
        sa.column("grant_type", sa.String()),
        sa.column("note", sa.Text()),
        sa.column("created_at", sa.DateTime()),
    )
    resource_table = sa.table(
        "ui_permission_resources",
        sa.column("resource_type", sa.String()),
        sa.column("resource_key", sa.String()),
        sa.column("label", sa.String()),
        sa.column("required_permission_code", sa.String()),
        sa.column("route_path", sa.String()),
        sa.column("method", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("sort_order", sa.Integer()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )

    op.bulk_insert(role_table, [
        {**role, "is_system": True, "is_active": True, "created_at": now, "updated_at": now}
        for role in ROLES
    ])
    op.bulk_insert(permission_table, [
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
    ])
    role_ids = dict(bind.execute(sa.text("select code, id from roles")).all())
    permission_ids = dict(bind.execute(sa.text("select code, id from permissions")).all())
    role_permission_rows = []
    for role_code, permission_codes in ROLE_PERMISSION_CODES.items():
        for permission_code in permission_codes:
            role_permission_rows.append({
                "role_id": role_ids[role_code],
                "permission_id": permission_ids[permission_code],
                "created_at": now,
            })
    op.bulk_insert(role_permission_table, role_permission_rows)
    op.bulk_insert(resource_table, [
        {
            "resource_type": resource_type,
            "resource_key": resource_key,
            "label": label,
            "required_permission_code": permission_code,
            "route_path": route_path,
            "method": method,
            "is_active": True,
            "sort_order": sort_order,
            "created_at": now,
            "updated_at": now,
        }
        for resource_type, resource_key, label, permission_code, route_path, method, sort_order in RESOURCES
    ])
    migrate_existing_user_permissions(bind, user_permission_table, permission_ids, now)


def migrate_existing_user_permissions(bind, user_permission_table, permission_ids: dict[str, int], now: datetime) -> None:
    try:
        rows = bind.execute(sa.text("select id, permissions_json from users")).all()
    except Exception:
        return
    migrated = []
    seen = set()
    for user_id, raw_permissions in rows:
        for code in parse_permissions_json(raw_permissions):
            permission_id = permission_ids.get(code)
            if not permission_id:
                continue
            key = (user_id, permission_id)
            if key in seen:
                continue
            seen.add(key)
            migrated.append({
                "user_id": user_id,
                "permission_id": permission_id,
                "grant_type": "ALLOW",
                "note": "Migrated from users.permissions_json",
                "created_at": now,
            })
    if migrated:
        op.bulk_insert(user_permission_table, migrated)


def parse_permissions_json(value) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
        except json.JSONDecodeError:
            return [item.strip() for item in value.split(",") if item.strip()]
        return parse_permissions_json(parsed)
    return []
