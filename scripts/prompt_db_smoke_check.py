#!/usr/bin/env python3
"""Verify Prompt DB migration, example catalog data, catalog API, and scene JSON builder."""

from __future__ import annotations

import os
import sys
import tempfile
import json
from pathlib import Path
from unittest.mock import patch

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


PROMPT_TABLES = {
    "prompt_scopes",
    "prompt_category_groups",
    "prompt_subcategories",
    "prompt_subcategory_keywords",
    "prompt_categories",
    "prompt_category_terms",
    "prompt_terms",
    "prompt_term_relations",
    "prompt_term_renderings",
    "prompt_rules",
    "prompt_templates",
    "prompt_generation_requests",
    "prompt_generation_outputs",
    "prompt_feedback",
    "prompt_system_prompts",
    "model_profiles",
}


def login_headers(client) -> dict[str, str]:
    response = client.post("/api/auth/login", json={"id": "dobedub", "password": "password"})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['accessToken']}"}


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="dobedub-prompt-db-smoke-") as tmp:
        database_path = Path(tmp) / "prompt-smoke.db"
        os.environ["DATABASE_URL"] = f"sqlite:///{database_path}"
        os.environ["PERSISTENCE_BACKEND"] = "db"

        config = Config(str(PROJECT_ROOT / "alembic.ini"))
        command.upgrade(config, "head")

        engine = create_engine(os.environ["DATABASE_URL"], future=True)
        tables = set(inspect(engine).get_table_names())
        missing = PROMPT_TABLES - tables
        assert not missing, f"Missing prompt tables: {sorted(missing)}"
        engine.dispose()

        from fastapi.testclient import TestClient
        from backend.app.main import app
        from backend.app.db.session import SessionLocal
        from backend.app.services.prompt_builder_service import apply_example_prompt_catalog

        raw_client = TestClient(app)
        admin_headers = login_headers(raw_client)

        class AuthedClient:
            def get(self, path: str, **kwargs):
                return raw_client.get(path, headers={**admin_headers, **kwargs.pop("headers", {})}, **kwargs)

            def post(self, path: str, **kwargs):
                return raw_client.post(path, headers={**admin_headers, **kwargs.pop("headers", {})}, **kwargs)

            def put(self, path: str, **kwargs):
                return raw_client.put(path, headers={**admin_headers, **kwargs.pop("headers", {})}, **kwargs)

        client = AuthedClient()
        with SessionLocal() as db:
            catalog = apply_example_prompt_catalog(db, force=True)
        assert catalog["groups"]
        positive_groups = [group for group in catalog["groups"] if group["scopeCode"] == "POSITIVE"]
        negative_groups = [group for group in catalog["groups"] if group["scopeCode"] == "NEGATIVE"]
        assert positive_groups and negative_groups
        work_style_group = next(group for group in positive_groups if group["code"] == "positive_work_style")
        genre_subcategory = next(subcategory for subcategory in work_style_group["subcategories"] if subcategory["code"] == "GENRE")
        assert genre_subcategory["terms"]
        assert len(catalog["categories"]) >= 30
        genre_category = next(category for category in catalog["categories"] if category["code"] == "GENRE")
        action_category = next(category for category in catalog["categories"] if category["code"] == "CHARACTER_ACTION")
        subject_category = next(category for category in catalog["categories"] if category["code"] == "SUBJECT_TYPE")
        category_codes = {category["code"] for category in catalog["categories"]}
        expected_extension_categories = {
            "POSITIVE_ROOT",
            "NEGATIVE_ROOT",
            "OBJECT_ACTION",
            "MOTION_SPEED",
            "MOTION_INTENSITY",
            "CAMERA_ANGLE",
            "LENS_TYPE",
            "FOCUS_STYLE",
            "CLOTHING",
            "POSE",
            "GAZE_DIRECTION",
            "FACIAL_EXPRESSION",
            "EMOTION",
            "ANIMATION_STYLE",
            "RENDERING_STYLE",
            "SCENE_TRANSITION",
            "SHOT_DURATION",
            "NEGATIVE_QUALITY",
            "NEGATIVE_CAMERA",
            "NEGATIVE_TEXT",
            "NEGATIVE_IDENTITY",
            "NEGATIVE_EXCLUSION",
        }
        assert expected_extension_categories.issubset(category_codes)
        positive_root = next(category for category in catalog["categories"] if category["code"] == "POSITIVE_ROOT")
        negative_root = next(category for category in catalog["categories"] if category["code"] == "NEGATIVE_ROOT")
        assert genre_category["parentCategoryId"] == positive_root["id"]
        assert next(category for category in catalog["categories"] if category["code"] == "NEGATIVE_TEXT")["parentCategoryId"] == negative_root["id"]
        root_update_response = client.put(f"/api/prompts/categories/{positive_root['id']}", json={
            **positive_root,
            "nameKo": "수정 불가",
        })
        assert root_update_response.status_code == 400
        root_deactivate_response = client.post(f"/api/prompts/categories/{negative_root['id']}/deactivate")
        assert root_deactivate_response.status_code == 400
        assert genre_category["selectionMode"] == "multi"
        assert action_category["selectionMode"] == "multi"
        assert subject_category["selectionMode"] == "single"
        assert subject_category["required"] is True
        assert genre_category["scopeType"] == "GLOBAL"
        assert next(category for category in catalog["categories"] if category["code"] == "LENS_TYPE")["selectionMode"] == "single"
        assert next(category for category in catalog["categories"] if category["code"] == "CLOTHING")["scopeType"] == "ENTITY"
        assert next(category for category in catalog["categories"] if category["code"] == "NEGATIVE_TEXT")["scopeType"] == "OUTPUT"
        assert any(
            term["code"] == "negative_identity_drift"
            for category in catalog["categories"]
            for term in category["terms"]
        )
        assert any(
            term["code"] == "negative_new_objects"
            for category in catalog["categories"]
            for term in category["terms"]
        )
        term_ids = [
            term["id"]
            for category in catalog["categories"]
            for term in category["terms"]
            if term["code"] in {"genre_cinematic", "subject_person", "action_gentle_walk", "negative_distortion"}
        ]
        assert len(term_ids) == 4
        subject_term_ids = [
            term["id"]
            for category in catalog["categories"]
            for term in category["terms"]
            if term["code"] in {"subject_person", "subject_product"}
        ]
        assert len(subject_term_ids) == 2

        catalog_response = client.get("/api/prompts/catalog")
        assert catalog_response.status_code == 200
        assert catalog_response.json()["templates"]
        assert catalog_response.json()["relations"]
        assert catalog_response.json()["groups"]

        admin_group_response = client.post("/api/prompts/category-groups", json={
            "code": "positive_admin_group",
            "scopeType": "POSITIVE",
            "nameKo": "관리 카테고리",
            "nameEn": "Admin Category",
            "description": "created by smoke test",
            "sortOrder": 998,
        })
        assert admin_group_response.status_code == 200, admin_group_response.text
        admin_group = next(group for group in admin_group_response.json()["groups"] if group["code"] == "positive_admin_group")
        admin_group_update = client.put(f"/api/prompts/category-groups/{admin_group['id']}", json={
            **admin_group,
            "scopeType": "POSITIVE",
            "nameKo": "관리 카테고리 수정",
        })
        assert admin_group_update.status_code == 200, admin_group_update.text
        updated_group = next(group for group in admin_group_update.json()["groups"] if group["code"] == "positive_admin_group")
        assert updated_group["nameKo"] == "관리 카테고리 수정"

        admin_category_response = client.post("/api/prompts/categories", json={
            "code": "TEST_ADMIN_CATEGORY",
            "groupId": updated_group["id"],
            "groupCode": updated_group["code"],
            "scopeType": "SCENE",
            "selectionMode": "multi",
            "required": False,
            "maxSelectCount": 2,
            "nameKo": "관리 테스트",
            "nameEn": "Admin Test",
            "description": "created by smoke test",
            "sortOrder": 999,
        })
        assert admin_category_response.status_code == 200, admin_category_response.text
        admin_catalog = admin_category_response.json()
        admin_category = next(category for category in admin_catalog["categories"] if category["code"] == "TEST_ADMIN_CATEGORY")
        admin_group_after_category = next(group for group in admin_catalog["groups"] if group["id"] == updated_group["id"])
        assert any(subcategory["code"] == "TEST_ADMIN_CATEGORY" for subcategory in admin_group_after_category["subcategories"])
        assert admin_category["selectionMode"] == "multi"
        admin_category_update = client.put(f"/api/prompts/categories/{admin_category['id']}", json={
            **admin_category,
            "selectionMode": "single",
            "nameKo": "관리 테스트 수정",
        })
        assert admin_category_update.status_code == 200, admin_category_update.text
        updated_category = next(category for category in admin_category_update.json()["categories"] if category["code"] == "TEST_ADMIN_CATEGORY")
        assert updated_category["selectionMode"] == "single"
        admin_term_response = client.post("/api/prompts/terms", json={
            "categoryId": updated_category["id"],
            "code": "test_admin_term",
            "canonicalKey": "test.admin.term",
            "labelKo": "관리 term",
            "labelEn": "admin term",
            "promptText": "admin prompt term",
            "negativeText": "",
            "riskLevel": "NONE",
            "sortOrder": 10,
        })
        assert admin_term_response.status_code == 200, admin_term_response.text
        term_category = next(category for category in admin_term_response.json()["categories"] if category["id"] == updated_category["id"])
        admin_term = next(term for term in term_category["terms"] if term["code"] == "test_admin_term")
        assert admin_term["promptText"] == "admin prompt term"
        admin_group_after_term = next(group for group in admin_term_response.json()["groups"] if group["id"] == updated_group["id"])
        admin_subcategory_after_term = next(subcategory for subcategory in admin_group_after_term["subcategories"] if subcategory["code"] == "TEST_ADMIN_CATEGORY")
        admin_group_term = next(term for term in admin_subcategory_after_term["terms"] if term["code"] == "test_admin_term")
        assert admin_group_term["promptText"] == "admin prompt term"
        term_deactivate_response = client.post(f"/api/prompts/terms/{admin_term['id']}/deactivate")
        assert term_deactivate_response.status_code == 200, term_deactivate_response.text
        term_deactivated_category = next(category for category in term_deactivate_response.json()["categories"] if category["id"] == updated_category["id"])
        assert not any(term["code"] == "test_admin_term" for term in term_deactivated_category["terms"])
        term_deactivated_group = next(group for group in term_deactivate_response.json()["groups"] if group["id"] == updated_group["id"])
        term_deactivated_subcategory = next(subcategory for subcategory in term_deactivated_group["subcategories"] if subcategory["code"] == "TEST_ADMIN_CATEGORY")
        assert not any(term["code"] == "test_admin_term" for term in term_deactivated_subcategory["terms"])
        category_deactivate_response = client.post(f"/api/prompts/categories/{updated_category['id']}/deactivate")
        assert category_deactivate_response.status_code == 200, category_deactivate_response.text
        assert not any(category["code"] == "TEST_ADMIN_CATEGORY" for category in category_deactivate_response.json()["categories"])
        group_deactivate_response = client.post(f"/api/prompts/category-groups/{updated_group['id']}/deactivate")
        assert group_deactivate_response.status_code == 200, group_deactivate_response.text
        assert not any(group["code"] == "positive_admin_group" for group in group_deactivate_response.json()["groups"])

        schema_response = client.get("/api/prompts/scene-schema")
        assert schema_response.status_code == 200
        scene_schema = schema_response.json()
        assert scene_schema["$id"].endswith("/scene-json-v1.schema.json")
        assert scene_schema["properties"]["version"]["const"] == "1.0"
        assert scene_schema["properties"]["scenes"]["minItems"] == 1
        assert "entity" not in scene_schema["$defs"]
        assert "relation" not in scene_schema["$defs"]
        assert "description" in scene_schema["$defs"]["sceneItem"]["required"]

        scene_response = client.post("/api/prompts/scene", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "termIds": term_ids,
            "constraints": {
                "preserve_identity": True,
                "avoid_new_objects": True,
                "i2v_mode": True,
            },
        })
        assert scene_response.status_code == 200, scene_response.text
        scene = scene_response.json()
        assert scene["requestId"].startswith("prompt_req_")
        assert "cinematic WAN image-to-video shot" in scene["positivePromptDraft"]
        assert "gentle, natural walking motion" in scene["positivePromptDraft"]
        assert "gentle walking motion" not in scene["positivePromptDraft"]
        assert "distorted anatomy" in scene["negativePromptDraft"]
        assert scene["modelProfile"]["modelFamily"] == "WAN"
        assert scene["scene"]["version"] == "1.0"
        assert set(scene_schema["required"]).issubset(scene["scene"].keys())
        first_scene = scene["scene"]["scenes"][0]
        assert set(scene_schema["$defs"]["sceneItem"]["required"]).issubset(first_scene.keys())
        assert "entities" not in first_scene
        assert "relations" not in first_scene
        assert "person" in first_scene["summary"]
        assert "preserve identity" not in first_scene["summary"]
        assert scene["constraints"]["preserve_identity"] is True
        assert "gentle walking" in first_scene["summary"]
        assert len(scene["usedTermIds"]) == 5
        assert any(warning["code"] == "term_implied" for warning in scene["warnings"])
        assert any(warning["code"] == "term_recommended" for warning in scene["warnings"])

        from backend.app.services.prompt_builder_service import (
            scene_json_v1_schema_validation_available,
            validate_scene_json_v1,
            validate_scene_json_v1_with_schema,
        )

        assert validate_scene_json_v1(scene["scene"]) == []
        assert validate_scene_json_v1_with_schema(scene["scene"]) == []
        assert scene_json_v1_schema_validation_available()
        invalid_scene = {**scene["scene"], "scenes": []}
        invalid_errors = validate_scene_json_v1(invalid_scene)
        invalid_schema_errors = validate_scene_json_v1_with_schema(invalid_scene)
        assert invalid_errors
        assert invalid_schema_errors
        assert invalid_errors[0]["code"] == "scene_schema_invalid"
        assert invalid_schema_errors[0]["code"] == "scene_schema_invalid"

        validation_response = client.post("/api/prompts/scene", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "termIds": subject_term_ids,
        })
        assert validation_response.status_code == 200, validation_response.text
        validation_scene = validation_response.json()
        assert "person" in validation_scene["scene"]["scenes"][0]["summary"]
        assert any(warning["code"] == "selection_limit_trimmed" for warning in validation_scene["warnings"])

        description_response = client.post("/api/prompts/scene", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "termIds": term_ids,
            "description": "main person gently turns toward the camera",
        })
        assert description_response.status_code == 200, description_response.text
        description_scene = description_response.json()["scene"]
        description_scene_item = description_scene["scenes"][0]
        assert description_scene_item["description"] == "main person gently turns toward the camera"
        assert "main person gently turns toward the camera" in description_scene_item["summary"]
        assert "entities" not in description_scene_item
        assert "relations" not in description_scene_item
        assert validate_scene_json_v1_with_schema(description_scene) == []

        description_only_response = client.post("/api/prompts/scene", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "termIds": [],
            "description": "girl dance exciting",
        })
        assert description_only_response.status_code == 200, description_only_response.text
        description_only_scene = description_only_response.json()
        description_only_item = description_only_scene["scene"]["scenes"][0]
        assert description_only_scene["usedTermIds"] == []
        assert description_only_item["summary"] == "girl dance exciting"
        assert description_only_item["description"] == "girl dance exciting"
        assert validate_scene_json_v1_with_schema(description_only_scene["scene"]) == []

        extension_term_ids = [
            term["id"]
            for category in catalog["categories"]
            for term in category["terms"]
            if term["code"] in {
                "subject_person",
                "object_remain_stable",
                "motion_speed_slow",
                "motion_intensity_subtle",
                "camera_angle_eye_level",
                "lens_standard",
                "focus_subject_locked",
                "clothing_preserve",
                "pose_preserve",
                "gaze_camera",
                "expression_soft_smile",
                "emotion_calm",
                "animation_realistic_i2v",
                "rendering_photoreal",
                "transition_none",
                "duration_short_3s",
                "negative_low_quality",
                "negative_camera_shake",
                "negative_text_overlay",
            }
        ]
        extension_response = client.post("/api/prompts/scene", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "termIds": extension_term_ids,
        })
        assert extension_response.status_code == 200, extension_response.text
        extension_scene = extension_response.json()["scene"]["scenes"][0]
        assert "remain stable" in extension_scene["summary"]
        assert "preserve clothing" in extension_scene["summary"]
        assert "eye-level angle" in extension_scene["camera"]["angle"]
        assert "standard lens" in extension_scene["camera"]["lens"]
        assert "subject-locked focus" in extension_scene["camera"]["focus"]
        assert "realistic image-to-video" in extension_scene["style"]["animationStyle"]
        assert "photorealistic rendering" in extension_scene["style"]["renderingStyle"]
        assert "slow motion pace" in extension_scene["motion"]["speed"]
        assert "subtle motion intensity" in extension_scene["motion"]["intensity"]
        assert "avoid low quality" in extension_scene["negativeTerms"]

        camera_term_ids = [
            term["id"]
            for category in catalog["categories"]
            for term in category["terms"]
            if term["code"] in {"camera_static", "camera_slow_tracking", "subject_person"}
        ]
        conflict_response = client.post("/api/prompts/scene", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "termIds": camera_term_ids,
        })
        assert conflict_response.status_code == 200, conflict_response.text
        conflict_scene = conflict_response.json()
        assert any(warning["code"] == "term_relation_conflict" for warning in conflict_scene["warnings"])

        generate_response = client.post("/api/prompts/generate", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "provider": "mock",
            "termIds": term_ids,
            "scene": scene["scene"],
            "constraints": scene["constraints"],
        })
        assert generate_response.status_code == 200, generate_response.text
        generated = generate_response.json()
        assert generated["provider"] == "mock"
        assert "preserve identity" in generated["positivePrompt"]
        assert "identity drift" in generated["negativePrompt"]

        system_prompt_response = client.get("/api/prompts/system-prompt")
        assert system_prompt_response.status_code == 200, system_prompt_response.text
        system_prompt = system_prompt_response.json()
        assert system_prompt["code"] == "qwen_wan_i2v_positive"
        assert system_prompt["modelFamily"] == "qwen"
        assert "DOBEDUB STUDIO" in system_prompt["promptText"]
        assert "Negative prompts are managed separately" in system_prompt["promptText"]

        custom_system_prompt_text = (
            "CUSTOM QWEN SYSTEM PROMPT. Return only valid JSON with positivePrompt, "
            "negativePrompt, warnings. negativePrompt must be an empty string."
        )
        save_system_prompt_response = client.put("/api/prompts/system-prompt", json={
            "promptText": custom_system_prompt_text,
        })
        assert save_system_prompt_response.status_code == 200, save_system_prompt_response.text
        saved_system_prompt = save_system_prompt_response.json()
        assert saved_system_prompt["promptText"] == custom_system_prompt_text

        class FakeRunpodResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"status":"COMPLETED","output":"{\\"choices\\":[{\\"tokens\\":[\\"Final JSON:\\\\n{\\\\\\"positivePrompt\\\\\\":\\\\\\"runpod cinematic prompt\\\\\\",\\\\\\"negativePrompt\\\\\\":\\\\\\"runpod negative prompt\\\\\\",\\\\\\"warnings\\\\\\":[]}\\"]}] }"}'

        os.environ["PROMPT_LLM_PROVIDER"] = "runpod_vllm"
        os.environ["PROMPT_LLM_API_KEY"] = "test_prompt_llm_key"
        os.environ["PROMPT_LLM_ENDPOINT_ID"] = "test_prompt_llm_endpoint"
        with patch("backend.app.services.prompt_llm_client.urllib.request.urlopen", return_value=FakeRunpodResponse()) as fake_urlopen:
            runpod_generate_response = client.post("/api/prompts/generate", json={
                "workflowId": "1-images.json",
                "segmentIndex": 1,
                "language": "ko",
                "termIds": term_ids,
                "scene": scene["scene"],
                "constraints": scene["constraints"],
            })
        os.environ["PROMPT_LLM_PROVIDER"] = "mock"
        assert runpod_generate_response.status_code == 200, runpod_generate_response.text
        runpod_generated = runpod_generate_response.json()
        assert runpod_generated["provider"] == "runpod_vllm"
        assert runpod_generated["positivePrompt"] == "runpod cinematic prompt."
        assert runpod_generated["negativePrompt"] == "runpod negative prompt"
        runpod_request = fake_urlopen.call_args[0][0]
        assert runpod_request.full_url.endswith("/test_prompt_llm_endpoint/runsync")
        runpod_request_body = json.loads(runpod_request.data.decode("utf-8"))
        assert "CUSTOM QWEN SYSTEM PROMPT" in json.dumps(runpod_request_body, ensure_ascii=False)

        class FakePlaceholderRunpodResponse:
            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc, traceback):
                return False

            def read(self):
                return b'{"status":"COMPLETED","output":"{\\"positivePrompt\\":\\"string\\",\\"negativePrompt\\":\\"\\",\\"warnings\\":[\\"string\\"]}"}'

        os.environ["PROMPT_LLM_PROVIDER"] = "runpod_vllm"
        with patch("backend.app.services.prompt_llm_client.urllib.request.urlopen", return_value=FakePlaceholderRunpodResponse()):
            placeholder_generate_response = client.post("/api/prompts/generate", json={
                "workflowId": "1-images.json",
                "segmentIndex": 1,
                "language": "ko",
                "termIds": term_ids,
                "scene": scene["scene"],
                "constraints": scene["constraints"],
            })
        os.environ["PROMPT_LLM_PROVIDER"] = "mock"
        assert placeholder_generate_response.status_code == 200, placeholder_generate_response.text
        placeholder_generated = placeholder_generate_response.json()
        assert placeholder_generated["positivePrompt"] != "string."
        assert "person" in placeholder_generated["positivePrompt"].lower()
        assert any(warning["code"] == "llm_response_placeholder" for warning in placeholder_generated["warnings"])

        invalid_generate_response = client.post("/api/prompts/generate", json={
            "workflowId": "1-images.json",
            "segmentIndex": 1,
            "language": "ko",
            "provider": "mock",
            "termIds": term_ids,
            "scene": invalid_scene,
            "constraints": scene["constraints"],
        })
        assert invalid_generate_response.status_code == 400
        assert "Scene JSON v1 validation failed" in invalid_generate_response.text

        feedback_response = client.post("/api/prompts/feedback", json={
            "outputId": generated["outputId"],
            "rating": 5,
            "editedPositivePrompt": generated["positivePrompt"],
            "editedNegativePrompt": generated["negativePrompt"],
            "notes": "smoke test",
        })
        assert feedback_response.status_code == 201, feedback_response.text
        assert feedback_response.json()["rating"] == 5

    print("OK prompt db smoke check passed")


if __name__ == "__main__":
    main()
