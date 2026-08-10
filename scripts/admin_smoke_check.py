#!/usr/bin/env python3
"""Smoke check for admin users, workflow activation, and prompt catalog access."""

from __future__ import annotations

import os
import json
import shutil
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def copy_workflow_fixture(workflows_dir: Path) -> None:
    workflows_dir.mkdir(parents=True, exist_ok=True)
    for name in ("1-images.json", "1-images.paramconfig.json"):
        shutil.copy2(PROJECT_ROOT / "workflows" / name, workflows_dir / name)


def login_headers(client, user_id: str, password: str) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"id": user_id, "password": password})
    assert response.status_code == 200, response.text
    token = response.json()["accessToken"]
    return {"Authorization": f"Bearer {token}"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-admin-smoke-") as tmp:
        tmp_path = Path(tmp)
        database_path = tmp_path / "admin-smoke.db"
        workflows_dir = tmp_path / "workflows"
        data_dir = tmp_path / "data"
        metadata_dir = tmp_path / "metadata"
        copy_workflow_fixture(workflows_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        metadata_dir.mkdir(parents=True, exist_ok=True)

        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["PERSISTENCE_BACKEND"] = "db"
        os.environ["WORKFLOWS_DIR"] = str(workflows_dir)
        os.environ["STUDIO_DATA_DIR"] = str(data_dir)
        os.environ["METADATA_DIR"] = str(metadata_dir)

        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(config, "head")

        engine = create_engine(os.environ["DATABASE_URL"], future=True)
        inspector = inspect(engine)
        columns = {column["name"] for column in inspect(engine).get_columns("users")}
        assert {"password_hash", "permissions_json", "is_active", "last_login_at"}.issubset(columns)
        assert {"roles", "permissions", "role_permissions", "user_permissions", "ui_permission_resources"}.issubset(set(inspector.get_table_names()))
        engine.dispose()

        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        admin_headers = login_headers(client, "dobedub", "password")

        users_response = client.get("/api/admin/users", headers=admin_headers)
        assert users_response.status_code == 200, users_response.text
        users_payload = users_response.json()
        users = users_payload["items"]
        assert any(user["id"] == "dobedub" and user["role"] == "SUPER_ADMIN" for user in users)
        governance = users_payload["permissionGovernance"]
        assert any(role["code"] == "OPERATOR" and "jobs:run" in role["permissionCodes"] for role in governance["roles"])
        assert any(permission["code"] == "prompts:reuse" for permission in governance["permissions"])
        assert any(resource["resourceKey"] == "action.generate_video" for resource in governance["resources"])
        permissions_response = client.get("/api/admin/permissions", headers=admin_headers)
        assert permissions_response.status_code == 200, permissions_response.text
        assert any(role["code"] == "SUPER_ADMIN" for role in permissions_response.json()["roles"])
        assert any(resource["resourceKey"] == "api.admin.roles_write" and resource["requiredPermissionCode"] == "roles:write" for resource in permissions_response.json()["resources"])

        reader_create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "reader1",
            "name": "Reader One",
            "role": "VIEWER",
            "permissions": ["users:read"],
            "isActive": True,
            "password": "reader-pass",
        })
        assert reader_create_response.status_code == 200, reader_create_response.text
        reader_headers = login_headers(client, "reader1", "reader-pass")
        viewer_create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "viewer1",
            "name": "Viewer One",
            "role": "VIEWER",
            "permissions": [],
            "isActive": True,
            "password": "viewer-pass",
        })
        assert viewer_create_response.status_code == 200, viewer_create_response.text
        viewer_headers = login_headers(client, "viewer1", "viewer-pass")

        denied_users_response = client.get(
            "/api/admin/users",
            headers=viewer_headers,
        )
        assert denied_users_response.status_code == 403, denied_users_response.text
        allowed_users_response = client.get(
            "/api/admin/users",
            headers=reader_headers,
        )
        assert allowed_users_response.status_code == 200, allowed_users_response.text
        role_write_denied_response = client.put(
            "/api/admin/roles/VIEWER/permissions",
            headers=reader_headers,
            json={"permissionCodes": ["workflows:read"]},
        )
        assert role_write_denied_response.status_code == 403, role_write_denied_response.text
        denied_workflow_write_response = client.post(
            "/api/admin/workflows",
            json={"workflowId": "denied.json", "workflowJson": {}},
            headers=viewer_headers,
        )
        assert denied_workflow_write_response.status_code == 403, denied_workflow_write_response.text

        role_update_response = client.put(
            "/api/admin/roles/VIEWER/permissions",
            headers=admin_headers,
            json={"permissionCodes": ["workflows:read", "history:read"]},
        )
        assert role_update_response.status_code == 200, role_update_response.text
        updated_viewer_role = next(role for role in role_update_response.json()["roles"] if role["code"] == "VIEWER")
        assert updated_viewer_role["permissionCodes"] == ["workflows:read", "history:read"]

        create_response = client.post("/api/admin/users", headers=admin_headers, json={
            "id": "operator1",
            "name": "Operator One",
            "email": "operator1@example.com",
            "role": "OPERATOR",
            "permissions": ["jobs:create"],
            "isActive": True,
            "password": "operator-pass",
        })
        assert create_response.status_code == 200, create_response.text
        created_user = create_response.json()["user"]
        assert created_user["id"] == "operator1"
        assert created_user["permissions"] == ["jobs:create"]
        assert "jobs:run" in created_user["rolePermissionCodes"]
        assert "jobs:create" in created_user["extraPermissionCodes"]
        assert "jobs:run" in created_user["effectivePermissionCodes"]

        update_response = client.put("/api/admin/users/operator1", headers=admin_headers, json={
            "name": "Operator Updated",
            "email": "operator-updated@example.com",
            "role": "ADMIN",
            "permissions": ["admin:workflows"],
            "isActive": True,
        })
        assert update_response.status_code == 200, update_response.text
        assert update_response.json()["user"]["role"] == "ADMIN"

        reset_response = client.post("/api/admin/users/operator1/reset-password", headers=admin_headers, json={"password": "new-pass"})
        assert reset_response.status_code == 200, reset_response.text

        login_response = client.post("/api/auth/login", json={
            "id": "operator1",
            "password": "new-pass",
        })
        assert login_response.status_code == 200, login_response.text
        assert login_response.json()["user"]["lastLoginAt"]

        state_update_response = client.put("/api/admin/users/operator1", headers=admin_headers, json={
            "name": "Operator Updated",
            "role": "ADMIN",
            "permissions": ["admin:workflows"],
            "isActive": "false",
        })
        assert state_update_response.status_code == 200, state_update_response.text
        state_updated_user = next(user for user in state_update_response.json()["items"] if user["id"] == "operator1")
        assert state_updated_user["isActive"] is False
        inactive_login_response = client.post("/api/auth/login", json={
            "id": "operator1",
            "password": "new-pass",
        })
        assert inactive_login_response.status_code == 400, inactive_login_response.text
        assert "inactive" in inactive_login_response.text.lower()

        default_admin_state_response = client.put("/api/admin/users/dobedub", headers=admin_headers, json={
            "name": "장균은",
            "role": "SUPER_ADMIN",
            "permissions": ["admin:*"],
            "isActive": False,
        })
        assert default_admin_state_response.status_code == 400, default_admin_state_response.text
        assert "Default super admin" in default_admin_state_response.text

        missing_login_response = client.post("/api/auth/login", json={
            "id": "missing-user",
            "password": "any-pass",
        })
        assert missing_login_response.status_code == 400, missing_login_response.text

        deactivate_user_response = client.post("/api/admin/users/operator1/deactivate", headers=admin_headers)
        assert deactivate_user_response.status_code == 200, deactivate_user_response.text
        inactive_user = next(user for user in deactivate_user_response.json()["items"] if user["id"] == "operator1")
        assert inactive_user["isActive"] is False

        workflows_response = client.get("/api/admin/workflows", headers=admin_headers)
        assert workflows_response.status_code == 200, workflows_response.text
        workflows = workflows_response.json()["items"]
        assert len(workflows) == 1 and workflows[0]["id"] == "1-images.json"
        assert workflows[0]["active"] is True

        deactivate_workflow_response = client.post("/api/admin/workflows/1-images.json/deactivate", headers=admin_headers)
        assert deactivate_workflow_response.status_code == 200, deactivate_workflow_response.text
        active_workflows_response = client.get("/api/workflows", headers=admin_headers)
        assert active_workflows_response.status_code == 200, active_workflows_response.text
        assert active_workflows_response.json() == []

        activate_workflow_response = client.post("/api/admin/workflows/1-images.json/activate", headers=admin_headers)
        assert activate_workflow_response.status_code == 200, activate_workflow_response.text
        active_workflows_response = client.get("/api/workflows", headers=admin_headers)
        assert active_workflows_response.status_code == 200, active_workflows_response.text
        assert [workflow["id"] for workflow in active_workflows_response.json()] == ["1-images.json"]

        register_response = client.post("/api/admin/workflows", headers=admin_headers, json={
            "workflowId": "registered-test.json",
            "description": "registered by smoke test",
            "workflowJson": json.loads((PROJECT_ROOT / "workflows" / "1-images.json").read_text(encoding="utf-8")),
        })
        assert register_response.status_code == 200, register_response.text
        registered = next(item for item in register_response.json()["items"] if item["id"] == "registered-test.json")
        assert registered["active"] is False
        assert registered["paramConfigGenerated"] is True
        assert register_response.json()["paramConfigGenerated"] is True
        assert register_response.json()["metadataUpdated"] is True
        assert register_response.json()["segmentDefaultsUpdated"] is True
        assert (workflows_dir / "registered-test.json").exists()
        assert (workflows_dir / "registered-test.paramconfig.json").exists()
        generated_config = json.loads((workflows_dir / "registered-test.paramconfig.json").read_text(encoding="utf-8"))
        assert generated_config["segments"][0]["params"]["steps"]["default"] == 4
        assert generated_config["segments"][0]["params"]["cfg_scale"]["default"] == 1
        assert generated_config["segments"][0]["params"]["width"]["default"] == 720
        assert generated_config["segments"][0]["params"]["height"]["default"] == 720
        generated_defaults = json.loads((data_dir / "segment-defaults.json").read_text(encoding="utf-8"))
        assert generated_defaults["registered-test.json"]["segments"][0]["config"]["steps"] == 4
        assert generated_defaults["registered-test.json"]["segments"][0]["config"]["cfgScale"] == 1
        assert generated_defaults["registered-test.json"]["segments"][0]["config"]["width"] == 720
        assert generated_defaults["registered-test.json"]["segments"][0]["config"]["height"] == 720
        assert "seed" not in generated_defaults["registered-test.json"]["segments"][0]["config"]
        defaults_response = client.get("/api/workflows/registered-test.json/segment-defaults", headers=admin_headers)
        assert defaults_response.status_code == 200, defaults_response.text
        assert defaults_response.json()["segments"][0]["config"]["steps"] == 4
        metadata_response = client.get("/api/workflows/registered-test.json/widget-metadata", headers=admin_headers)
        assert metadata_response.status_code == 200, metadata_response.text
        assert metadata_response.json()["workflowId"] == "registered-test.json"

        catalog_response = client.get("/api/prompts/catalog", headers=admin_headers)
        assert catalog_response.status_code == 200, catalog_response.text
        assert "categories" in catalog_response.json()
        legacy_catalog_response = client.get("/api/admin/prompt-catalog", headers=admin_headers)
        assert legacy_catalog_response.status_code == 404, legacy_catalog_response.text

    print("OK admin smoke check passed")


if __name__ == "__main__":
    main()
