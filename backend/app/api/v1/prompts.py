from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from backend.app.core.security import CurrentUser, require_any_permission, require_permission
from backend.app.db.session import get_db
from backend.app.services import studio_api_service
from backend.app.services.prompt_builder_service import (
    build_scene_json,
    deactivate_prompt_category_group,
    deactivate_prompt_category,
    deactivate_prompt_term,
    generate_prompt,
    prompt_catalog,
    save_prompt_feedback,
    scene_json_v1_schema,
    upsert_prompt_category_group,
    upsert_prompt_category,
    upsert_prompt_keyword,
)
from backend.app.services.prompt_system_prompt_service import get_prompt_system_prompt, save_prompt_system_prompt

router = APIRouter(prefix="/prompts", tags=["prompts"])


@router.get("")
def prompts(_: CurrentUser = Depends(require_any_permission(("prompts:build", "prompts:reuse")))):
    return studio_api_service.prompt_options()


@router.get("/reusable")
def reusable_prompts(
    keyword: str = "",
    workflowId: str = "",
    minRating: int | None = None,
    reviewedOnly: bool = False,
    reuseEligible: bool | None = None,
    limit: int = 50,
    _: CurrentUser = Depends(require_permission("prompts:reuse")),
):
    try:
        return {
            "items": studio_api_service.reusable_prompts(
                keyword=keyword,
                workflow_id=workflowId,
                min_rating=minRating,
                reviewed_only=reviewedOnly,
                reuse_eligible=reuseEligible,
                limit=limit,
            )
        }
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Reusable prompt query failed: {exc}") from exc


@router.get("/catalog")
def catalog(_: CurrentUser = Depends(require_any_permission(("prompts:build", "prompts:reuse", "prompt-catalog:read", "prompt-catalog:write"))), db: Session = Depends(get_db)):
    try:
        return prompt_catalog(db)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt DB is not ready: {exc}") from exc


@router.get("/scene-schema")
def scene_schema(_: CurrentUser = Depends(require_any_permission(("prompts:build", "prompts:reuse")))):
    return scene_json_v1_schema()


@router.get("/system-prompt")
def system_prompt(_: CurrentUser = Depends(require_permission("prompts:build")), db: Session = Depends(get_db)):
    try:
        return get_prompt_system_prompt(db)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt system prompt load failed: {exc}") from exc


@router.put("/system-prompt")
def update_system_prompt(payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return save_prompt_system_prompt(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt system prompt save failed: {exc}") from exc


@router.post("/category-groups")
def create_category_group(payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return upsert_prompt_category_group(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt category save failed: {exc}") from exc


@router.put("/category-groups/{group_id}")
def update_category_group(group_id: int, payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return upsert_prompt_category_group(db, payload, group_id=group_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt category save failed: {exc}") from exc


@router.post("/category-groups/{group_id}/deactivate")
def deactivate_category_group(group_id: int, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return deactivate_prompt_category_group(db, group_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt category deactivate failed: {exc}") from exc


@router.post("/categories")
def create_category(payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return upsert_prompt_category(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt category save failed: {exc}") from exc


@router.put("/categories/{category_id}")
def update_category(category_id: int, payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return upsert_prompt_category(db, payload, category_id=category_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt category save failed: {exc}") from exc


@router.post("/categories/{category_id}/deactivate")
def deactivate_category(category_id: int, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return deactivate_prompt_category(db, category_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt category deactivate failed: {exc}") from exc


@router.post("/terms")
def create_term(payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return upsert_prompt_keyword(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt term save failed: {exc}") from exc


@router.put("/terms/{term_id}")
def update_term(term_id: int, payload: dict, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return upsert_prompt_keyword(db, payload, term_id=term_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt term save failed: {exc}") from exc


@router.post("/terms/{term_id}/deactivate")
def deactivate_term(term_id: int, _: CurrentUser = Depends(require_permission("prompt-catalog:write")), db: Session = Depends(get_db)):
    try:
        return deactivate_prompt_term(db, term_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt term deactivate failed: {exc}") from exc


@router.post("/scene")
def scene(payload: dict, _: CurrentUser = Depends(require_permission("prompts:build")), db: Session = Depends(get_db)):
    try:
        return build_scene_json(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt scene build failed: {exc}") from exc


@router.post("/generate")
def generate(payload: dict, _: CurrentUser = Depends(require_permission("prompts:build")), db: Session = Depends(get_db)):
    try:
        return generate_prompt(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt generation failed: {exc}") from exc


@router.post("/feedback", status_code=201)
# B-03: 평가는 검수 행위다 - 생성 권한(prompts:build)이 아니라 리뷰 권한(prompts:review)을
# 요구한다. ADMIN 역할은 review는 있지만 build는 없어 이전에는 이 엔드포인트를 호출할 수
# 없었다(B-02가 새로 연결한 3f의 "프롬프트 생성 품질" 평가 UI가 정작 ADMIN에게는 403이었음).
def feedback(payload: dict, _: CurrentUser = Depends(require_permission("prompts:review")), db: Session = Depends(get_db)):
    try:
        return save_prompt_feedback(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"Prompt feedback failed: {exc}") from exc
