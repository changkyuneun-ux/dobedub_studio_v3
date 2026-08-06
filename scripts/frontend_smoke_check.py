#!/usr/bin/env python3
"""Static smoke check for the React frontend skeleton."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path
import re

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


REQUIRED_FILES = [
    "frontend/package.json",
    "frontend/index.html",
    "frontend/vite.config.ts",
    "frontend/tsconfig.json",
    "frontend/tsconfig.node.json",
    "frontend/src/main.tsx",
    "frontend/src/styles.css",
    "frontend/src/api/client.ts",
    "frontend/src/router.ts",
]


def main() -> None:
    missing = [path for path in REQUIRED_FILES if not (PROJECT_ROOT / path).exists()]
    assert not missing, f"Missing frontend files: {missing}"

    package_json = json.loads((PROJECT_ROOT / "frontend/package.json").read_text(encoding="utf-8"))
    assert package_json["scripts"]["dev"].startswith("vite")
    assert "react" in package_json["dependencies"]
    assert "vite" in package_json["dependencies"]

    main_tsx = (PROJECT_ROOT / "frontend/src/main.tsx").read_text(encoding="utf-8")
    assert "function LoginView" in main_tsx
    assert "function StudioShell" in main_tsx
    assert "apiClient.workflows" in main_tsx
    assert "workflowSchema" in main_tsx
    assert "apiClient.upload" in main_tsx
    assert "sessionStorage" in main_tsx
    assert "routeFromLocation" in main_tsx
    assert 'route: StudioRoute' in main_tsx
    assert "service-status-group" in main_tsx
    assert "ComfyUI: <strong>{comfyStatus}</strong>" in main_tsx
    assert "Qwen: <strong>{qwenStatus}</strong>" in main_tsx
    assert "function qwenStatusLabel" in main_tsx
    assert 'onNavigate("history")' in main_tsx
    assert 'onNavigate("status")' in main_tsx
    assert 'onNavigate("metadata")' in main_tsx
    assert 'onNavigate("manual")' in main_tsx
    assert 'onNavigate("admin")' in main_tsx
    assert 'onNavigate("studio")' in main_tsx
    assert "createSegmentsFromSchema" in main_tsx
    assert "Payload Preview" in main_tsx
    assert "configControls" in main_tsx
    assert "apiClient.createJob" in main_tsx
    assert "apiClient.jobStatus" in main_tsx
    assert "apiClient.cancelJob" in main_tsx
    assert "GENERATE VIDEO" in main_tsx
    assert "Cancel Generation" in main_tsx
    assert "Log Stream" in main_tsx
    assert "selectedOutputAsset" in main_tsx
    assert "finalOutputAsset" in main_tsx
    assert "result-card" in main_tsx
    assert "failure-card" in main_tsx
    assert '"No job"' not in main_tsx
    assert "Recent History" not in main_tsx
    assert "function HistoryModal" in main_tsx
    assert "function StatusModal" in main_tsx
    assert "function ManualModal" in main_tsx
    assert 'sandbox="allow-scripts"' in main_tsx
    assert "function MetadataModal" in main_tsx
    assert "function AdminConsoleModal" in main_tsx
    assert "Admin Console" in main_tsx
    assert "Users" in main_tsx
    assert "Roles & Permissions" in main_tsx
    assert "Workflows" in main_tsx
    assert "Prompt Catalog" in main_tsx
    assert "Save User" in main_tsx
    assert "사용자 정보" in main_tsx
    assert "사용자 등록" in main_tsx
    assert "Role Default Permissions" in main_tsx
    assert "Extra Permissions" in main_tsx
    assert "Effective Permissions" in main_tsx
    assert "Feature Resource Mapping" in main_tsx
    assert "admin-status-badge" in main_tsx
    assert "Save Workflow" in main_tsx
    assert "Workflow JSON 불러오기" in main_tsx
    assert "selectedAdminWorkflow" in main_tsx
    assert "loadWorkflowFile" in main_tsx
    assert "PromptCatalogAdminContent" in main_tsx
    assert "admin-catalog-panel" in main_tsx
    assert "onCatalogVisible" in main_tsx
    assert 'activeTab === "catalog" && canManageCatalog && !catalog && !catalogLoading' in main_tsx
    assert "Reload Catalog" not in main_tsx
    assert "Refresh Catalog" in main_tsx
    assert "adminUserFormFrom" in main_tsx
    assert "adminPermissionsFromText" in main_tsx
    assert "function PromptBuilderModal" in main_tsx
    assert "function SystemPromptEditor" in main_tsx
    assert "System Prompt" in main_tsx
    assert "promptBuilderPanel" in main_tsx
    assert "promptSystemPromptText" in main_tsx
    assert "apiClient.promptSystemPrompt" in main_tsx
    assert "apiClient.savePromptSystemPrompt" in main_tsx
    assert "function PromptEntityRelationEditor" not in main_tsx
    assert "function PromptCatalogAdminModal" in main_tsx
    assert "Prompt Catalog Admin" in main_tsx
    assert "Manage Catalog" not in main_tsx
    assert "Admin Console에서 카테고리와 key word를 등록하세요." in main_tsx
    assert "prompt-taxonomy-tree" in main_tsx
    assert "promptAccordionDefaultKeys" in main_tsx
    assert "return new Set<string>();" in main_tsx
    assert "toggleCatalogAccordion" in main_tsx
    assert "aria-expanded" in main_tsx
    assert "activeCatalogAdminLevel" in main_tsx
    assert "관리할 항목을 선택하세요." in main_tsx
    assert "상위 카테고리 정보" in main_tsx
    assert "선택 서브 카테고리 정보" in main_tsx
    assert "categoryGroupCodeFromForm" in main_tsx
    assert "subcategoryCodeFromForm" in main_tsx
    assert "Save Category" in main_tsx
    assert "Save Sub Category" in main_tsx
    assert "Save Key Word" in main_tsx
    assert "String(category.legacyCategoryId || category.id)" in main_tsx
    assert "promptTermCodeFromForm" in main_tsx
    assert "Canonical<input" not in main_tsx
    assert "Risk<select" not in main_tsx
    assert "Sort<input" not in main_tsx
    assert "promptCatalogAdminScopes" in main_tsx
    assert "FIXED_PROMPT_ROOT_CODES" in main_tsx
    assert "Prompt Builder" in main_tsx
    assert "Selected Key Words" in main_tsx
    assert "function SelectedKeywordBox" in main_tsx
    assert "defaultNegativePrompt: string;" in main_tsx
    assert "baseNegativePrompt={selectedSegment?.defaultNegativePrompt || selectedSegment?.negativePrompt || \"\"}" in main_tsx
    assert "const positiveKeywordDraft = promptKeywordText(selectedKeywords.positive);" in main_tsx
    assert "const negativeKeywordDraft = promptKeywordText(selectedKeywords.negative);" in main_tsx
    assert "const negativePromptAddition = generated?.negativePrompt || negativeKeywordDraft;" in main_tsx
    assert "const negativePrompt = combinePromptText(baseNegativePrompt, negativePromptAddition);" in main_tsx
    assert "function promptKeywordText" in main_tsx
    assert "function combinePromptText" in main_tsx
    assert "const keywordText = keywords.map((keyword) => keyword.labelEn || keyword.code).join(\", \");" in main_tsx
    assert "<p className=\"selected-keyword-text\">{keywordText}</p>" in main_tsx
    assert "selectedPromptKeywordsByScope" in main_tsx
    assert "selected-keyword-grid" in main_tsx
    assert "const sceneDetailDraft = sceneDescription.trim();" in main_tsx
    assert "const hasPositiveInput = Boolean(positiveKeywordDraft || sceneDetailDraft);" in main_tsx
    assert "const canBuildScene = hasPositiveInput;" in main_tsx
    assert "const positivePrompt = generated?.positivePrompt || positiveKeywordDraft || sceneDetailDraft;" in main_tsx
    assert "Scene Detail" in main_tsx
    assert "sceneDescription={promptSceneDescription}" in main_tsx
    assert "description: promptSceneDescription.trim()" in main_tsx
    assert "Build Scene JSON" not in main_tsx
    assert "Scene Detail Settings" not in main_tsx
    assert "Scene Actions" not in main_tsx
    assert "Advanced Entity Settings" not in main_tsx
    assert "Add Entity" not in main_tsx
    assert "Add Relation" not in main_tsx
    assert "PREDICATE_TEMPLATES" not in main_tsx
    assert "promptBuilderValidationHints" not in main_tsx
    assert "selectionMode" in main_tsx
    assert "findPromptTermCategory" in main_tsx
    assert "Clear Selection" in main_tsx
    assert "Refresh Catalog" in main_tsx
    assert "Apply Generated Prompt" in main_tsx
    assert "Apply Keyword / Scene Draft" in main_tsx
    assert "buildPromptSceneRequest" in main_tsx
    assert "const sceneForGeneration = promptScene || await buildPromptSceneRequest();" in main_tsx
    assert "Scene JSON 자동 생성 후" in main_tsx
    assert "promptOverride?.positivePrompt ?? promptGenerated?.positivePrompt ?? promptScene?.positivePromptDraft ?? \"\"" in main_tsx
    assert "negativePromptAddition: promptOverride?.negativePrompt ?? combinePromptText(segment.defaultNegativePrompt || segment.negativePrompt, negativePromptAddition)" in main_tsx
    assert "positivePrompt: positivePrompt || segment.positivePrompt" not in main_tsx
    assert "negativePrompt: negativePrompt || segment.negativePrompt" not in main_tsx
    assert "negativePromptAddition: negativePrompt || segment.negativePromptAddition" not in main_tsx
    assert "disabled={loading || !canBuildScene} onClick={onGenerate}" in main_tsx
    assert "disabled={!hasPositiveInput && !generated}" in main_tsx
    assert "onBuild={() => void buildPromptScene()}" not in main_tsx
    assert "onClick={() => onApply({" in main_tsx
    assert "source: generated ? \"Generated Prompt\" : \"Prompt Builder\"" in main_tsx
    assert "function PromptSceneStructurePreview" in main_tsx
    assert "Scene Structure" in main_tsx
    assert "flattenNamedLists" in main_tsx
    assert "promptEntitiesForScene" not in main_tsx
    assert "splitPromptBuilderList" not in main_tsx
    assert "clearPromptBuilderSelection" in main_tsx
    assert "apiClient.promptCatalog" in main_tsx
    assert "seedPromptCatalog" not in main_tsx
    assert "Seed Catalog" not in main_tsx
    assert "apiClient.savePromptCategory" in main_tsx
    assert "apiClient.deactivatePromptCategory" in main_tsx
    assert "apiClient.savePromptTerm" in main_tsx
    assert "apiClient.deactivatePromptTerm" in main_tsx
    assert "apiClient.buildPromptScene" in main_tsx
    assert "entities: promptEntitiesForScene(promptEntities, keyframes)" not in main_tsx
    assert "apiClient.generatePrompt" in main_tsx
    assert 'provider: "mock"' not in main_tsx
    assert "applyPromptSceneToSegment" in main_tsx
    assert "Generate Prompt" in main_tsx
    assert "Task History" in main_tsx
    assert "Task History & Result List" in main_tsx
    assert "System Status" in main_tsx
    assert "Test ComfyUI" in main_tsx
    assert "ComfyUI RunPod" in main_tsx
    assert "Qwen Prompt LLM" in main_tsx
    assert "Prompt LLM" not in main_tsx.replace("Qwen Prompt LLM", "")
    assert "dobedub studio 사용자 매뉴얼" in main_tsx
    assert "Workflow Metadata" in main_tsx
    assert "Load Past Prompts" not in main_tsx
    assert "Generate Report" not in main_tsx
    assert "apiClient.systemStatus" in main_tsx
    assert "apiClient.manualHtml" in main_tsx
    assert "apiClient.workflowWidgetMetadata" in main_tsx
    assert "apiClient.rebuildMetadata" in main_tsx
    assert "apiClient.deleteHistory" in main_tsx
    assert "재작업" in main_tsx
    assert "삭제한 모든 자료" in main_tsx
    assert "createKeyframesFromHistory" in main_tsx
    assert '<ProtectedImage src={keyframe.previewUrl} alt={`Input ${keyframe.index}`} />' in main_tsx
    assert '<img src={keyframe.previewUrl}' not in main_tsx
    rework_handler = re.search(r"async function applyHistoryRework\(item: HistoryItem\) \{(?P<body>.*?)\n  \}", main_tsx, re.DOTALL)
    assert rework_handler is not None
    assert 'onNavigate("studio");' in rework_handler.group("body")

    styles_css = (PROJECT_ROOT / "frontend/src/styles.css").read_text(encoding="utf-8")
    assert ".prompt-builder-modal" in styles_css
    assert ".service-status-group" in styles_css
    assert ".status-pill.dry-run" in styles_css
    assert ".status-pill.mock" in styles_css
    assert ".prompt-builder-side-nav" in styles_css
    assert ".prompt-builder-side-nav button.is-active" in styles_css
    assert ".system-prompt-editor" in styles_css
    assert ".system-prompt-textarea" in styles_css
    assert ".system-prompt-actions" in styles_css
    assert ".admin-modal" in styles_css
    assert ".admin-layout" in styles_css
    assert ".admin-list" in styles_css
    assert ".admin-form" in styles_css
    assert ".admin-catalog-panel" in styles_css
    assert ".admin-catalog-toolbar" in styles_css
    assert ".admin-detail-card" in styles_css
    assert ".admin-status-badge" in styles_css
    assert ".admin-row.is-selected::before" in styles_css
    assert ".workflow-file-loader" in styles_css
    assert ".toolbar button.is-active" in styles_css
    assert "height: min(860px, calc(100vh - 48px));" in styles_css
    assert ".prompt-builder-layout" in styles_css
    assert "grid-template-columns: minmax(200px, 20%) minmax(0, 1fr);" in styles_css
    assert "grid-template-rows: auto 108px auto;" in styles_css
    assert "height: 190px;" in styles_css
    assert ".selected-keyword-text" in styles_css
    assert "overflow-wrap: anywhere;" in styles_css
    assert "height: 100%;" in styles_css
    assert "overscroll-behavior: contain;" in styles_css

    api_client = (PROJECT_ROOT / "frontend/src/api/client.ts").read_text(encoding="utf-8")
    assert "system?: SystemStatusResponse;" in api_client
    assert "legacy?: SystemStatusResponse;" in api_client
    assert "/api/health" in api_client
    assert "/api/system/status" in api_client
    assert "/api/runpod/connection" in api_client
    assert "/manual" in api_client
    assert "/api/metadata/status" in api_client
    assert "/api/metadata/models" in api_client
    assert "/api/metadata/rebuild" in api_client
    assert "/api/workflows" in api_client
    assert "/schema" in api_client
    assert "/widget-metadata" in api_client
    assert "/api/history" in api_client
    assert "/api/prompts/catalog" in api_client
    assert "PromptSystemPromptResponse" in api_client
    assert "/api/prompts/system-prompt" in api_client
    assert "/api/prompts/scene-schema" in api_client
    assert "/api/prompts/seed" not in api_client
    assert "/api/prompts/category-groups" in api_client
    assert "/api/prompts/categories" in api_client
    assert "/api/prompts/terms" in api_client
    assert "/api/prompts/scene" in api_client
    assert "description?: string" in api_client
    build_scene_match = re.search(r"buildPromptScene: \(payload: \{(?P<body>.*?)\}\) =>", api_client, re.DOTALL)
    assert build_scene_match is not None
    build_scene_payload = build_scene_match.group("body")
    assert "entities?" not in build_scene_payload
    assert "relations?" not in build_scene_payload
    assert "/api/prompts/generate" in api_client
    assert "/api/prompts/feedback" in api_client
    assert "/api/uploads" in api_client
    assert "/api/jobs" in api_client
    assert "/delete" in api_client
    assert "/api/auth/login" in api_client
    assert "assetBlob: (path: string) => requestBlob(path)" in api_client
    assert "/api/admin/users" in api_client
    assert "/api/admin/workflows" in api_client
    assert "/api/admin/workflows/${encodeURIComponent(workflowId)}/activate" in api_client
    assert "/api/admin/workflows/${encodeURIComponent(workflowId)}/deactivate" in api_client
    assert '"/api/login"' not in api_client

    prompt_llm_client = (PROJECT_ROOT / "backend/app/services/prompt_llm_client.py").read_text(encoding="utf-8")
    assert "positivePrompt must be one complete natural English sentence" in prompt_llm_client
    assert "positivePrompt and negativePrompt must be English comma-separated prompt text" not in prompt_llm_client
    assert "system_prompt: str | None = None" in prompt_llm_client
    assert "negative_key_present" in prompt_llm_client
    assert "def _normalize_positive_sentence" in prompt_llm_client

    system_prompt_service = (PROJECT_ROOT / "backend/app/services/prompt_system_prompt_service.py").read_text(encoding="utf-8")
    assert "DEFAULT_QWEN_WAN_I2V_SYSTEM_PROMPT" in system_prompt_service
    assert "Negative prompts are managed separately" in system_prompt_service
    assert "active_prompt_system_prompt_text" in system_prompt_service

    router = (PROJECT_ROOT / "frontend/src/router.ts").read_text(encoding="utf-8")
    assert "/studio/login" in router
    assert "/studio/app" in router
    assert "/studio/history" in router
    assert "/studio/status" in router
    assert "/studio/metadata" in router
    assert "/studio/manual" in router
    assert "/studio/admin" in router

    legacy_html = (PROJECT_ROOT / "index.html").read_text(encoding="utf-8")
    legacy_app = (PROJECT_ROOT / "src/app.js").read_text(encoding="utf-8")
    assert "Load Past Prompts" not in legacy_html
    assert "Generate Report" not in legacy_html
    assert "loadPromptButton" not in legacy_html
    assert "generateReportButton" not in legacy_html
    assert "promptModal" not in legacy_html
    assert "Load Past Prompts" not in legacy_app
    assert "Generate Report" not in legacy_app
    assert "loadPromptButton" not in legacy_app
    assert "generateReportButton" not in legacy_app
    assert "promptModal" not in legacy_app

    with tempfile.TemporaryDirectory(prefix="dobedub-frontend-smoke-") as tmp:
        tmp_path = Path(tmp)
        os.environ["DATABASE_URL"] = f"sqlite:///{tmp_path / 'frontend-smoke.db'}"
        os.environ["PERSISTENCE_BACKEND"] = "db"
        os.environ["STUDIO_DATA_DIR"] = str(tmp_path / "data")
        command.upgrade(Config(str(PROJECT_ROOT / "alembic.ini")), "head")

        from fastapi.testclient import TestClient
        from backend.app.main import app

        client = TestClient(app)
        for path in ["/studio", "/studio/app", "/studio/history", "/studio/status", "/studio/metadata", "/studio/manual", "/studio/admin"]:
            response = client.get(path)
            assert response.status_code == 200
            assert "DOBEDUB STUDIO React frontend" in response.text or '<div id="root">' in response.text
        login_response = client.post("/api/auth/login", json={"id": "dobedub", "password": "password", "name": "장균은"})
        assert login_response.status_code == 200
        assert login_response.json()["user"]["name"] == "장균은"
        assert login_response.json()["accessToken"]
        admin_headers = {"Authorization": f"Bearer {login_response.json()['accessToken']}"}
        workflows_response = client.get("/api/workflows", headers=admin_headers)
        assert workflows_response.status_code == 200
        workflows = workflows_response.json()
        assert isinstance(workflows, list) and workflows
        schema_response = client.get(f"/api/workflows/{workflows[0]['id']}/schema", headers=admin_headers)
        assert schema_response.status_code == 200
        schema = schema_response.json()
        assert schema["keyframeCount"] >= 1
        assert schema["segments"][0]["configControls"]
        dist_assets = sorted((PROJECT_ROOT / "frontend" / "dist" / "assets").glob("*")) if (PROJECT_ROOT / "frontend" / "dist" / "assets").exists() else []
        if dist_assets:
            asset_response = client.get(f"/studio/assets/{dist_assets[0].name}")
            assert asset_response.status_code == 200
        favicon_response = client.get("/studio/favicon.png")
        assert favicon_response.status_code == 200
        assert favicon_response.headers.get("content-type", "").startswith("image/png")
        assert favicon_response.content[:8] == b"\x89PNG\r\n\x1a\n"

    print("OK frontend smoke check passed")


if __name__ == "__main__":
    main()
