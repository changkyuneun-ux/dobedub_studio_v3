#!/usr/bin/env python3
"""Smoke check for RBAC permission catalog, feature mapping, and API guards."""

from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def login_headers(client, user_id: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"id": user_id, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-rbac-smoke-") as tmp:
        tmp_path = Path(tmp)
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'rbac-smoke.db'}"
        os.environ["PERSISTENCE_BACKEND"] = "db"
        os.environ["STUDIO_DATA_DIR"] = str(tmp_path / "data")
        os.environ["RUNPOD_DRY_RUN"] = "1"
        command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")

        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        admin_headers = login_headers(client, "dobedub", "password")
        operator_create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "operator",
            "name": "Operator",
            "role": "OPERATOR",
            "permissions": [],
            "isActive": True,
            "password": "operator-pass",
        })
        assert operator_create_response.status_code == 200, operator_create_response.text
        viewer_create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "viewer",
            "name": "Viewer",
            "role": "VIEWER",
            "permissions": [],
            "isActive": True,
            "password": "viewer-pass",
        })
        assert viewer_create_response.status_code == 200, viewer_create_response.text
        # B-03: ADMIN은 prompts:review는 있지만 prompts:build는 없다 - 별도 사용자로
        # 만들어야 "리뷰 권한만으로 평가를 저장할 수 있는지"를 실제로 검증할 수 있다.
        reviewer_admin_create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "reviewer-admin",
            "name": "Reviewer Admin",
            "role": "ADMIN",
            "permissions": [],
            "isActive": True,
            "password": "reviewer-admin-pass",
        })
        assert reviewer_admin_create_response.status_code == 200, reviewer_admin_create_response.text
        operator_headers = login_headers(client, "operator", "operator-pass")
        viewer_headers = login_headers(client, "viewer", "viewer-pass")
        reviewer_admin_headers = login_headers(client, "reviewer-admin", "reviewer-admin-pass")

        governance_response = client.get("/api/admin/permissions", headers=admin_headers)
        assert governance_response.status_code == 200, governance_response.text
        governance = governance_response.json()
        permission_codes = {permission["code"] for permission in governance["permissions"]}
        resource_permissions = {
            resource["requiredPermissionCode"]
            for resource in governance["resources"]
            if resource.get("isActive", True)
        }
        missing = resource_permissions - permission_codes
        assert not missing, f"Feature resources reference unknown permissions: {sorted(missing)}"
        assert any(role["code"] == "OPERATOR" and "jobs:run" in role["permissionCodes"] for role in governance["roles"])
        assert any(resource["resourceKey"] == "action.history_delete" for resource in governance["resources"])
        assert any(resource["resourceKey"] == "api.admin.roles_write" and resource["requiredPermissionCode"] == "roles:write" for resource in governance["resources"])
        # B-03: POST /api/prompts/feedback는 이제 prompts:review 전용 카탈로그 행을
        # 따로 갖는다(generate/scene을 함께 뭉뚱그리던 api.prompts, 여전히 prompts:build,
        # 와는 구분됨) - 7b 화면이 정확한 값을 보여주는지 확인.
        assert any(
            resource["resourceKey"] == "api.prompt_feedback" and resource["requiredPermissionCode"] == "prompts:review"
            for resource in governance["resources"]
        )
        assert any(resource["resourceKey"] == "api.prompts" and resource["requiredPermissionCode"] == "prompts:build" for resource in governance["resources"])

        assert client.get("/api/workflows").status_code == 401
        assert client.get(
            "/api/admin/users",
            headers={"X-User-Role": "SUPER_ADMIN", "X-User-Permissions": "admin:*"},
        ).status_code == 401
        os.environ["AUTH_TRUST_PROXY_HEADERS"] = "1"
        assert client.get(
            "/api/admin/users",
            headers={"X-User-Role": "SUPER_ADMIN", "X-User-Permissions": "admin:*"},
        ).status_code == 401
        os.environ.pop("AUTH_TRUST_PROXY_HEADERS", None)
        assert client.get("/api/workflows", headers=viewer_headers).status_code == 200
        assert client.post("/api/jobs", headers=viewer_headers, json={}).status_code == 403
        assert client.get("/api/history?page=1&pageSize=10", headers=viewer_headers).status_code == 200

        assert client.get("/api/admin/users", headers=operator_headers).status_code == 403
        assert client.get("/api/admin/users", headers=admin_headers).status_code == 200
        assert client.post("/api/admin/workflows", headers=operator_headers, json={}).status_code == 403
        assert client.post("/api/history/nonexistent/delete", headers=operator_headers).status_code == 403

        assert client.get("/api/prompts/catalog", headers=operator_headers).status_code == 200
        assert client.put("/api/prompts/system-prompt", headers=operator_headers, json={"promptText": "blocked"}).status_code == 403

        # B-03: POST /api/prompts/feedback가 prompts:build에서 prompts:review로 바뀐 것을
        # 실제 401/403 경계로 검증한다. VIEWER(review도 build도 없음)는 여전히 403이어야
        # 하고, ADMIN(review는 있지만 build는 없음)은 권한 게이트를 통과해야 한다 - 통과
        # 이후 outputId가 없어 400(ValueError)이 나는 것으로 "403이 아니었다"를 구분한다.
        assert client.post("/api/prompts/feedback", headers=viewer_headers, json={"outputId": "does-not-exist"}).status_code == 403
        admin_feedback_response = client.post("/api/prompts/feedback", headers=reviewer_admin_headers, json={"outputId": "does-not-exist"})
        assert admin_feedback_response.status_code == 400, admin_feedback_response.text
        assert "Prompt output not found" in admin_feedback_response.text

        sandbox_super_create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "sandbox-super",
            "name": "Sandbox Super Admin",
            "role": "SUPER_ADMIN",
            "permissions": [],
            "isActive": True,
            "password": "sandbox-super-pass",
        })
        assert sandbox_super_create_response.status_code == 200, sandbox_super_create_response.text
        sandbox_super_headers = login_headers(client, "sandbox-super", "sandbox-super-pass")
        sandbox_super_session = client.get("/api/auth/session", headers=sandbox_super_headers)
        assert sandbox_super_session.status_code == 200, sandbox_super_session.text
        assert "admin:*" in sandbox_super_session.json()["user"]["effectivePermissionCodes"]
        assert client.get("/api/admin/sandbox-pod", headers=sandbox_super_headers).status_code == 200

        promoted_headers = login_headers(client, "operator", "operator-pass")
        promoted_update_response = client.put("/api/admin/users/operator", headers=admin_headers, json={
            "name": "Operator",
            "role": "SUPER_ADMIN",
            "permissions": [],
            "isActive": True,
        })
        assert promoted_update_response.status_code == 200, promoted_update_response.text
        promoted_session = client.get("/api/auth/session", headers=promoted_headers)
        assert promoted_session.status_code == 200, promoted_session.text
        assert promoted_session.json()["user"]["role"] == "SUPER_ADMIN"
        assert "admin:*" in promoted_session.json()["user"]["effectivePermissionCodes"]
        assert client.get("/api/admin/sandbox-pod", headers=promoted_headers).status_code == 200
        restored_operator_response = client.put("/api/admin/users/operator", headers=admin_headers, json={
            "name": "Operator",
            "role": "OPERATOR",
            "permissions": [],
            "isActive": True,
        })
        assert restored_operator_response.status_code == 200, restored_operator_response.text

        role_update_response = client.put(
            "/api/admin/roles/OPERATOR/permissions",
            headers=admin_headers,
            json={"permissionCodes": ["workflows:read", "history:read"]},
        )
        assert role_update_response.status_code == 200, role_update_response.text
        operator_headers_after_role_update = login_headers(client, "operator", "operator-pass")
        assert client.get("/api/workflows", headers=operator_headers_after_role_update).status_code == 200
        assert client.get("/api/metadata/status", headers=operator_headers_after_role_update).status_code == 403
        assert client.put(
            "/api/admin/roles/VIEWER/permissions",
            headers=operator_headers_after_role_update,
            json={"permissionCodes": ["workflows:read"]},
        ).status_code == 403

    print("OK RBAC permission smoke check passed")


if __name__ == "__main__":
    main()
