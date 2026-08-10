from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from backend.app.core.security import normalize_permissions, normalize_role
from backend.app.db.models import Permission, Role, RolePermission, UiPermissionResource, User, UserPermission


RESOURCE_CATALOG = [
    ("MENU", "top.history", "History/Saved Videos", "history:read", "/studio/history", None, 10),
    ("MENU", "top.status", "Check Status", "system:read", "/studio/status", None, 20),
    ("MENU", "top.metadata", "Metadata View", "metadata:read", "/studio/metadata", None, 30),
    ("MENU", "top.manual", "User Manual", "manual:read", "/studio/manual", None, 40),
    ("MENU", "top.admin.users", "Admin > Users", "users:read", "/studio/admin", None, 51),
    ("MENU", "top.admin.roles", "Admin > Permission Catalog", "roles:read", "/studio/admin", None, 52),
    ("MENU", "top.admin.workflows", "Admin > Workflows", "workflows:write", "/studio/admin", None, 53),
    ("MENU", "top.admin.catalog", "Admin > Prompt Catalog", "prompt-catalog:write", "/studio/admin", None, 54),
    ("MENU", "top.admin.sandbox_pod", "Admin > Sandbox Pod", "sandbox:read", "/studio/admin", None, 55),
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
    ("ACTION", "action.sandbox_pod_start", "Start Sandbox Pod", "sandbox:control", None, None, 220),
    ("ACTION", "action.sandbox_pod_stop", "Stop Sandbox Pod", "sandbox:control", None, None, 221),
    ("API", "api.admin.users", "Admin Users API", "users:read", "/api/admin/users", "GET", 300),
    ("API", "api.admin.users_write", "Admin User Write API", "users:write", "/api/admin/users", "POST/PUT", 301),
    ("API", "api.admin.roles", "Admin Roles API", "roles:read", "/api/admin/permissions", "GET", 310),
    ("API", "api.admin.roles_write", "Admin Role Permission Write API", "roles:write", "/api/admin/roles/{role_code}/permissions", "PUT", 311),
    ("API", "api.admin.workflows", "Admin Workflows API", "workflows:read", "/api/admin/workflows", "GET", 320),
    ("API", "api.jobs", "Jobs API", "jobs:run", "/api/jobs", "POST", 330),
    ("API", "api.jobs_cancel", "Job Cancel API", "jobs:cancel", "/api/jobs/{task_id}/cancel", "POST", 331),
    ("API", "api.history", "History API", "history:read", "/api/history", "GET", 340),
    ("API", "api.history_delete", "History Delete API", "history:delete", "/api/history/{task_id}/delete", "POST", 341),
    ("API", "api.metadata", "Metadata API", "metadata:read", "/api/metadata", "GET", 350),
    ("API", "api.metadata_rebuild", "Metadata Rebuild API", "metadata:rebuild", "/api/metadata/rebuild", "POST", 351),
    ("API", "api.prompts", "Prompt Builder API", "prompts:build", "/api/prompts", "POST", 360),
    ("API", "api.prompt_reuse", "Reusable Prompt API", "prompts:reuse", "/api/prompts/reusable", "GET", 361),
    # B-03: api.prompts(위 360)는 generate/scene 등 여러 POST /api/prompts/* 경로를
    # 뭉뚱그린 범용 라벨이라 여전히 prompts:build로 정확하다. /feedback만 검수
    # 권한으로 바뀌었으므로(평가는 검수 행위) api.prompt_reuse와 같은 방식으로
    # 전용 행을 새로 추가한다 - api.prompts를 prompts:review로 바꾸면 generate/scene에는
    # 오히려 틀린 정보가 된다.
    ("API", "api.prompt_feedback", "Prompt Feedback API", "prompts:review", "/api/prompts/feedback", "POST", 362),
    ("API", "api.admin.sandbox_pod", "Sandbox Pod Status API", "sandbox:read", "/api/admin/sandbox-pod", "GET", 370),
    ("API", "api.admin.sandbox_pod_control", "Sandbox Pod Control API", "sandbox:control", "/api/admin/sandbox-pod/start|stop", "POST", 371),
]


def permission_governance_catalog(session: Session) -> dict:
    ensure_permission_resource_catalog(session)
    roles = session.scalars(select(Role).order_by(Role.sort_order, Role.level.desc(), Role.code)).all()
    permissions = session.scalars(select(Permission).order_by(Permission.sort_order, Permission.code)).all()
    resources = session.scalars(select(UiPermissionResource).order_by(UiPermissionResource.sort_order, UiPermissionResource.resource_key)).all()
    role_permission_codes = role_permission_code_map(session)
    return {
        "roles": [
            {
                "id": role.id,
                "code": role.code,
                "name": role.name,
                "description": role.description,
                "level": role.level,
                "isSystem": bool(role.is_system),
                "isActive": bool(role.is_active),
                "sortOrder": role.sort_order,
                "permissionCodes": role_permission_codes.get(role.code, []),
            }
            for role in roles
        ],
        "permissions": [
            {
                "id": permission.id,
                "code": permission.code,
                "domain": permission.domain,
                "action": permission.action,
                "name": permission.name,
                "description": permission.description,
                "isSystem": bool(permission.is_system),
                "isActive": bool(permission.is_active),
                "sortOrder": permission.sort_order,
            }
            for permission in permissions
        ],
        "resources": [
            {
                "id": resource.id,
                "resourceType": resource.resource_type,
                "resourceKey": resource.resource_key,
                "label": resource.label,
                "requiredPermissionCode": resource.required_permission_code,
                "routePath": resource.route_path,
                "method": resource.method,
                "isActive": bool(resource.is_active),
                "sortOrder": resource.sort_order,
            }
            for resource in resources
        ],
    }


def update_role_permission_codes(session: Session, role_code: str, permission_codes: object) -> dict:
    normalized_role_code = normalize_role(role_code)
    role = session.scalar(select(Role).where(Role.code == normalized_role_code))
    if not role:
        raise ValueError("Role not found")
    if not role.is_active:
        raise ValueError("Inactive role cannot be updated")
    requested_codes = unique_permissions(normalize_permissions(permission_codes))
    if normalized_role_code == "SUPER_ADMIN" and "admin:*" not in requested_codes:
        raise ValueError("SUPER_ADMIN must keep admin:* permission")
    permissions = session.scalars(select(Permission).where(Permission.is_active.is_(True))).all()
    permission_by_code = {permission.code: permission for permission in permissions}
    missing = [code for code in requested_codes if code not in permission_by_code]
    if missing:
        raise ValueError(f"Unknown permission code(s): {', '.join(missing)}")
    session.execute(delete(RolePermission).where(RolePermission.role_id == role.id))
    now = datetime.utcnow()
    for code in requested_codes:
        session.add(RolePermission(role_id=role.id, permission_id=permission_by_code[code].id, created_at=now))
    role.updated_at = now
    session.commit()
    return permission_governance_catalog(session)


def ensure_permission_resource_catalog(session: Session) -> None:
    existing = {
        resource.resource_key: resource
        for resource in session.scalars(select(UiPermissionResource)).all()
    }
    changed = False
    now = datetime.utcnow()
    for resource_type, resource_key, label, permission_code, route_path, method, sort_order in RESOURCE_CATALOG:
        resource = existing.get(resource_key)
        if resource is None:
            session.add(UiPermissionResource(
                resource_type=resource_type,
                resource_key=resource_key,
                label=label,
                required_permission_code=permission_code,
                route_path=route_path,
                method=method,
                is_active=True,
                sort_order=sort_order,
                created_at=now,
                updated_at=now,
            ))
            changed = True
            continue
        resource_changed = False
        updates = {
            "resource_type": resource_type,
            "label": label,
            "required_permission_code": permission_code,
            "route_path": route_path,
            "method": method,
            "sort_order": sort_order,
        }
        for key, value in updates.items():
            if getattr(resource, key) != value:
                setattr(resource, key, value)
                resource_changed = True
        if not resource.is_active:
            resource.is_active = True
            resource_changed = True
        if resource_changed:
            resource.updated_at = now
            changed = True
    legacy_admin = existing.get("top.admin")
    if legacy_admin and legacy_admin.is_active:
        legacy_admin.is_active = False
        legacy_admin.updated_at = now
        changed = True
    if changed:
        session.commit()


def role_permission_code_map(session: Session) -> dict[str, list[str]]:
    rows = session.execute(
        select(Role.code, Permission.code)
        .join(RolePermission, RolePermission.role_id == Role.id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(Role.is_active.is_(True), Permission.is_active.is_(True))
        .order_by(Role.sort_order, Permission.sort_order, Permission.code)
    ).all()
    mapped: dict[str, list[str]] = {}
    for role_code, permission_code in rows:
        mapped.setdefault(str(role_code), []).append(str(permission_code))
    return mapped


def user_extra_permission_codes(session: Session, user_id: str) -> list[str]:
    rows = session.execute(
        select(Permission.code)
        .join(UserPermission, UserPermission.permission_id == Permission.id)
        .where(
            UserPermission.user_id == user_id,
            UserPermission.grant_type == "ALLOW",
            Permission.is_active.is_(True),
        )
        .order_by(Permission.sort_order, Permission.code)
    ).all()
    return [str(row[0]) for row in rows]


def effective_permission_codes(session: Session, user: User) -> list[str]:
    role_code = normalize_role(user.role)
    role_permissions = role_permission_code_map(session).get(role_code, [])
    extra_permissions = user_extra_permission_codes(session, user.id)
    legacy_permissions = normalize_permissions(user.permissions_json)
    return unique_permissions([*role_permissions, *legacy_permissions, *extra_permissions])


def user_permission_payload(session: Session, user: User) -> dict:
    role_code = normalize_role(user.role)
    role_permissions = role_permission_code_map(session).get(role_code, [])
    legacy_permissions = normalize_permissions(user.permissions_json)
    extra_permissions = user_extra_permission_codes(session, user.id)
    return {
        "rolePermissionCodes": role_permissions,
        "extraPermissionCodes": unique_permissions([*legacy_permissions, *extra_permissions]),
        "effectivePermissionCodes": unique_permissions([*role_permissions, *legacy_permissions, *extra_permissions]),
    }


def has_permission(permission_codes: list[str], required_permission: str) -> bool:
    if "admin:*" in permission_codes:
        return True
    if required_permission in permission_codes:
        return True
    domain = required_permission.split(":", 1)[0]
    return f"{domain}:*" in permission_codes


def unique_permissions(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        cleaned = str(value or "").strip()
        if not cleaned or cleaned in seen:
            continue
        seen.add(cleaned)
        result.append(cleaned)
    return result
