# 수행 리스트

각 항목은 독립 커밋 단위입니다. ID는 `5 API-DB Gap.dc.html`의 분류와 대응합니다.
우선순위: **P0** 다른 작업이 이것에 막힘 · **P1** 사용자가 바로 체감 · **P2** 이후.

> **문서 갱신: 2026-08-10 (Cowork 세션 대조).** 저장소가 origin/main 대비 15개 커밋 앞서 있음을 확인하고, 아래 체크박스를 실제 커밋 상태와 대조해 갱신했습니다. 커밋 해시는 로컬 전용이며 아직 push되지 않았습니다. 완료 표시는 코드 대조로 확인한 것만 체크했고, 문구를 글자 그대로 충족하지 못했지만 취지는 충족된 경우는 각주로 이유를 남겼습니다(임의 체크 없음).

---

## 0단계 · 착수 (P0)

### S-01 · 권한 코드와 역할 코드 정렬 — **완료** (커밋 `f73d6e9`)
설계 문서 전체는 아래 코드를 기준으로 작성되어 있습니다. 프론트 상수와 대조해 어긋나면 코드 쪽을 정본으로 삼고 설계 문서를 고치십시오(반대 방향 아님).

역할: `SUPER_ADMIN` `ADMIN` `OPERATOR` `VIEWER` — CREATOR·REVIEWER는 존재하지 않습니다.

주요 권한:
| 동작 | 권한 코드 |
|---|---|
| 작업 실행 | `jobs:run` |
| 작업 취소 | `jobs:cancel` |
| 이력 조회 | `history:read` |
| 이력 삭제 | `history:delete` |
| 자산 다운로드 | `jobs:run` 또는 `history:read` |
| 프롬프트 생성 | `prompts:build` |
| 프롬프트 평가 | `prompts:review` |
| 프롬프트 재사용 | `prompts:reuse` |
| 카탈로그 조회/편집 | `prompt-catalog:read` / `prompt-catalog:write` |
| 역할 조회/편집 | `roles:read` / `roles:write` |
| 사용자 조회/편집 | `users:read` / `users:write` |
| 워크플로 조회/편집/활성화 | `workflows:read` / `workflows:write` / `workflows:activate` |
| 메타데이터 조회/재생성 | `metadata:read` / `metadata:rebuild` |
| 시스템 상태 | `system:read` |
| Sandbox 조회/제어 | `sandbox:read` / `sandbox:control` |

완료 기준 — 프론트에서 쓰는 권한 문자열이 `ui_permission_resources.required_permission_code` 및 각 라우터의 `require_permission` 인자와 100% 일치. — *ADMIN_PERMISSION_OPTIONS 폴백 목록 정렬 확인(`history:write` 제거, `roles:read/write`·`workflows:activate`·`manual:read` 추가). CREATOR/REVIEWER 잔재 grep 결과 없음.*

---

## A · 신규 개발 (API·테이블 모두 없음)

착수 전 상태 그대로. 변경 없음.

### A-01 · 자산 목록 API — P1 — **완료** (API + 5a 화면. 5c는 A-02 대기로 범위 밖)
현재 `backend/app/api/v1/assets.py`에는 `POST /uploads`와 `GET /files/{asset_id}`만 있습니다. 화면 `5a` `5c`가 요구하는 목록 조회가 없습니다. `assets` 테이블은 이미 `asset_type` `size_bytes` `metadata_json` `created_at`을 갖고 있어 **마이그레이션 불필요**합니다.

- [x] `GET /api/assets` 추가 — 쿼리 `type` `workflowId` `from` `to` `page` `pageSize`, 권한 `history:read` — *history(D-03)와 동일하게 DB 전용으로 구현(`task_tracking_service.list_assets`/`assets_total`). 운영은 항상 `PERSISTENCE_BACKEND=db`라 repository 추상화를 통하지 않아도 실사용과 어긋나지 않음. `from`은 파이썬 예약어라 쿼리 파라미터명은 `from` 그대로 두고 `Query(alias="from")`로 받음.*
- [x] 응답에 연결된 taskId와 output_role(final/segment)을 포함 (`task_output_assets` 조인) — *`asset_id`당 최신 `TaskOutputAsset` 링크 1건을 조인. 아직 어떤 작업 출력에도 연결되지 않은 자산(업로드만 된 입력 이미지 등)은 `taskId`/`outputRole`이 빈 값으로 내려감 — `Create5aScreen`이 이 경우 "미연결"로 표기.*
- [x] 프론트 자산 화면 구현 — *`Create5aScreen`(5a) 구현. 설계의 컬렉션·태그·공개범위(PRIVATE/SHARED)·저장용량 바는 대응 백엔드가 전혀 없어(A-02 미착수, `assets` 테이블에 해당 컬럼 없음) 화면에서 제외 — 코드 주석에 사유 명시.*

완료 기준 — 자산 화면이 작업을 거치지 않고 직접 목록을 그린다. — *백엔드 TestClient로 필터(`type`/`workflowId`)·페이지네이션·조인 결과 확인, 프론트는 `tsc -b`/`vite build` 클린 확인. 실 데이터 화면 스크린샷 검증은 미실시.*

### A-02 · 컬렉션 — P2
`collection` 관련 코드가 저장소에 전무합니다.

- [ ] 마이그레이션: `collections`(id, name, created_by, created_at), `collection_items`(collection_id, asset_id, sort_order)
- [ ] `GET/POST /api/collections`, `POST /api/collections/{id}/items`
- [ ] 화면 `5c` 구현

### A-03 · 작업 알림 — P2
알림 저장·읽음 처리 구조가 없습니다. 두 안 중 택일이 필요합니다.

- 1안 · 폴링 결과를 클라이언트 토스트로 처리. 개발량 최소, 화면을 떠나면 소실.
- 2안 · `notifications` 테이블 + 읽음 상태 + `GET /api/notifications`.

- [ ] 방식 결정 후 구현. **결정 전에는 화면 `6e`를 건드리지 마십시오.**

### A-04 · 감사 로그 — P1
권한 변경, 카탈로그 수정, 사용자 역할 변경, Pod 제어, 이력 삭제 모두 기록이 없습니다. 각 테이블의 `updated_at`으로 마지막 시각만 알 수 있고 행위자와 변경 내용은 알 수 없습니다.

- [ ] 마이그레이션: `audit_logs`(id, actor_id, action, target_type, target_id, before_json, after_json, ip, created_at)
- [ ] 기록 지점: `update_role_permission_codes`, `upsert_admin_user`, `reset_admin_user_password`, `deactivate_admin_user`, `upsert_prompt_term/category/category_group`, `save_prompt_system_prompt`, `start/stop_sandbox_pod`, `delete_history_item`
- [ ] `GET /api/admin/audit-logs` — 권한 `roles:read`
- [ ] 화면의 `미구현` 배지 영역을 실제 데이터로 교체 (`3b` 변경 기록, `7c` 접근 이력, `5b` Pod 제어 이력, `4b`·`7a` 변경 이력)

주의 — 기록 실패가 본 동작을 막으면 안 됩니다. `job_service.py:310`의 기존 패턴(예외를 삼키고 진행)을 따르십시오.

### A-05 · 접근 이력 — P2
`users.last_login_at` 한 칸만 있어 최근 1회만 남습니다.

- [ ] A-04의 `audit_logs`에 `action='login'`으로 흡수. 별도 테이블 만들지 마십시오.

### A-06 · 세션 갱신 — P2
토큰 갱신 엔드포인트가 없어 만료되면 재로그인만 가능합니다.

- [ ] 만료 예고 배너는 토큰 `expiresAt`으로 클라이언트 계산 — **개발 없이 가능, 먼저 적용**
- [ ] 무중단 연장이 필요하면 `POST /api/auth/refresh` 추가

---

## B · 기존 코드 수정

### B-01 · 이력 페이지 크기 통일 — P1 — **완료** (커밋 `319ae22`)
`history.py`의 기본값은 `pageSize=50`, 프론트는 10을 보내고, 설계는 20입니다.

- [x] 백엔드 기본값 20으로 변경
- [x] 프론트는 사용자가 고른 값만 명시 전송 (20 / 50)
- [x] 화면 `3a`의 페이지네이션 구현 — 총 건수·현재 범위 표시 포함 — *기존(구버전) `HistoryModal` 안에 구현됨. 로직(페이지 크기 20/50, 총 건수·범위 표시)은 그대로 재사용 가능하지만, 신규 디자인 토큰·레이아웃 기반 `3a` 화면으로 이관할 때 UI는 다시 그려야 함 — TASKS.md E-03 참조.*

### B-02 · 프롬프트 평가 이중 저장 정리 — P0 — **완료** (커밋 `01ca385`)
평가를 담는 곳이 둘입니다. `task_prompts.quality_rating`(`PATCH /jobs/{id}/prompts/{n}/quality`)과 `prompt_feedback.rating`(`POST /prompts/feedback`). 두 번째는 편집한 프롬프트 원문까지 받습니다.

- [x] 역할 고정: **영상 결과 평가 → `task_prompts`**, **프롬프트 생성 품질 → `prompt_feedback`**
- [x] 화면은 `3f` Run 상세 한 곳에서만 평가를 남기도록 구현. 세그먼트 편집 화면에 평가 UI를 넣지 마십시오(설계에서 의도적으로 제거함) — *구버전 `HistoryDetail`(3f에 대응) 안에 `PromptReviewCard`/`PromptFeedbackCard`로 구현됨. B-01과 동일하게 신규 `3f` 화면 이관 시 로직만 재사용하고 UI는 재구현 — E-03 참조.*
- [x] `prompt_feedback.task_id`를 채워 두 기록이 연결되게 할 것

### B-03 · 피드백 저장 권한 — P1 — **완료** (커밋 `bb77be1`)
`POST /api/prompts/feedback`이 `prompts:build`를 요구합니다. 평가는 검수 행위입니다.

- [x] `require_permission("prompts:review")`로 변경
- [x] `ui_permission_resources` 시드도 함께 갱신 — *`permission_service.py`의 `RESOURCE_CATALOG`에 전용 행(`api.prompt_feedback`, 362)을 추가하는 방식으로 갱신함. `0009_rbac_feature_permissions` 마이그레이션 자체는 의도적으로 건드리지 않음 — 커밋 메시지가 `20260807_0011`(sandbox pod 권한 추가)도 같은 방식이었다는 기존 코드 관행을 근거로 듦. CHECKLIST.md 원문("0009 · permission_service.py 양쪽")과 문구가 다르지만, `ensure_permission_resource_catalog()`가 매 요청마다 `RESOURCE_CATALOG`를 `ui_permission_resources`에 upsert하므로 실질 결과는 동일함 — CHECKLIST.md 쪽 문구를 코드 관행에 맞게 갱신 필요(아래 참조).*

### B-04 · 실행 모드 노출 — P1 — **완료** (커밋 `7f8cc0d`)
`workflow_tasks.execution_mode` 기본값이 `"dry-run"`입니다. 사용자가 무엇을 실행하는지 화면에서 알 수 없습니다.

- [x] 실제 운영 기본이 무엇인지 확인 — *운영 배포 문서 4곳이 모두 `RUNPOD_DRY_RUN=0`(실제 실행)을 운영 필수값으로 명시함을 확인.*
- [ ] dry-run을 유지한다면 화면 `2f`(실행 전 확인)에 모드 배지를 추가하고, 실제 실행과 시각적으로 구분 — *해당 없음(아래 항목의 "항상 실제 실행" 경로를 택함).*
- [x] 항상 실제 실행이라면 기본값을 바꾸고 컬럼 용도를 문서화 — *`get_settings()`/`Settings.dry_run` 기본값을 `False`로 변경, `models.py`의 `execution_mode` 컬럼에 `Settings.dry_run` 기본값과의 관계를 주석으로 명시.*

### B-05 · 이력 삭제 방식 — P2
`delete_history_item`은 하드 삭제이고 `workflow_tasks`에 삭제 표시 컬럼이 없습니다. 삭제 사실 자체도 남지 않습니다.

- [ ] `deleted_at` 컬럼 추가, 조회에서 제외하는 방식으로 전환
- [ ] A-04와 함께 처리 (삭제 행위를 감사 로그에 기록)
- [ ] 화면 문구는 그대로 — 사용자에게는 복구 불가로 안내

### B-06 · 카탈로그를 신형 계층으로 일원화 — P0 · **결정됨** — **완료** (1~3단계, 4단계 중 컬럼 정리까지)
계층이 두 벌입니다.
- 구형 — `prompt_categories`(문자열 `group_code`) → `prompt_terms.category_id`
- 신형 — `prompt_scopes` → `prompt_category_groups` → `prompt_subcategories`(`legacy_category_id`로 구형과 연결)

**결정: 신형으로 구현합니다.** 화면 `4e` `3d`는 신형 계층만 편집하고, 구형은 이관 후 읽기 전용으로 남겼다가 제거합니다. 용어가 아직 구형 `prompt_terms.category_id`에 붙어 있는 것이 유일한 걸림돌입니다.

구현 순서 — 각 단계를 별도 커밋으로 나누고, 3단계까지는 기존 동작이 깨지지 않아야 합니다.

0. **선행 확인** — `prompt_catalog()`는 호출될 때마다 `sync_prompt_catalog_hierarchy()`를 먼저 실행해 구형→신형 계층을 자동 동기화합니다(`prompt_builder_service.py:520`). 이관 마이그레이션을 짜기 전에 이 함수가 무엇을 어떻게 채우는지 먼저 읽으십시오. 이미 신형 계층이 상당 부분 채워져 있을 수 있고, 그렇다면 1단계의 작업량이 크게 줄어듭니다. 전환 후에는 이 동기화 호출도 제거 대상입니다. — *4단계에서 `sync_prompt_catalog_hierarchy()` 호출부를 전부 제거 완료(코드에 제거 사유 주석 남김).*

1. **이관 마이그레이션** (`0012_migrate_terms_to_subcategories`) — **완료**
   - [x] `prompt_terms`의 각 행에 대해 `category_id` → `prompt_subcategories.legacy_category_id`로 대응되는 서브카테고리를 찾아 `prompt_subcategory_keywords`에 행 생성
   - [x] 대응되는 서브카테고리가 없는 용어는 해당 카테고리 그룹 아래 `기타` 서브카테고리를 만들어 수용 — **용어를 유실시키지 마십시오**
   - [x] 이관 건수와 미대응 건수를 마이그레이션 로그로 남길 것 — *`print()`로 scopesCreated/groupsCreated/subcategoriesCreated/termsTotal/termsViaOwnCategory/termsViaOtherFallback/키워드 링크 수 출력.*
   - [x] 다운그레이드 경로 작성

2. **읽기 경로 전환** — **완료** (커밋 `f05f89e`)
   - [x] `prompt_catalog()`가 `prompt_scopes → prompt_category_groups → prompt_subcategories → keywords` 순으로만 트리를 구성하도록 변경
   - [x] 응답에서 구형 `categories` 배열 제거. 프론트가 참조하던 `groupCode` 문자열은 `scopeCode`로 대체
   - [x] `generate_prompt`의 용어 조회도 신형 경로로 변경 — `used_term_ids`가 무엇을 가리키는지(term id인지 keyword id인지) 확정하고 문서화 — *`used_term_ids`/`selected_term_ids`는 `PromptTerm.id`로 확정, 코드 주석으로 명시(`prompt_builder_service.py:937` 부근).*

3. **쓰기 경로 전환** — **완료** (커밋 `bfad428`)
   - [x] `upsert_prompt_term`을 서브카테고리 기준으로 재작성 (`upsert_prompt_keyword`)
   - [x] 이 시점부터 구형 테이블에 신규 쓰기 금지

   참고 — 계층 편집 API는 **이미 있습니다.** `prompts.py`에 `POST/PUT /prompts/category-groups`, `/categories`, `/terms`와 각 `/deactivate`가 모두 존재하고 권한은 `prompt-catalog:write`입니다. 새로 만들 필요 없이 이 엔드포인트들이 신형 계층을 향하도록 서비스 함수만 바꾸면 됩니다.

4. **정리** — 컬럼 정리 완료 (커밋 `5d111ae`, `7d3029d`), 테이블 드롭은 보류
   - [x] `prompt_subcategories.legacy_category_id` 제거 (마이그레이션 `0013_cleanup_legacy_category_coupling`)
   - [ ] `prompt_terms`·`prompt_categories` 드롭 (별도 릴리스로 미루어도 무방) — *의도적으로 이연됨. 문서상 허용된 이연이라 각주만 남기고 미체크 유지.*

완료 기준 — `4e`에서 만든 서브카테고리와 용어가 `2b` 프롬프트 생성에 그대로 나타나고, 구형 테이블을 참조하는 코드가 없다. — *`build_scene_json`/`prompt_catalog` 모두 신형 계층만 참조하는 것을 코드로 확인. 단, 화면 `4e`/`3d`/`2b` 자체는 아직 신규 디자인으로 재구현되지 않아 최종 완료 기준의 "화면" 부분은 E-02/E-04에서 재검증 필요.*

### B-07 · SYSTEM 그룹 표기 — P2
DB 스코프는 POSITIVE 계열과 NEGATIVE 계열 둘뿐이고, 시스템 지시문은 `prompt_system_prompts`라는 별도 테이블입니다.

- [ ] 설계의 3그룹(POSITIVE·NEGATIVE·SYSTEM)은 **화면 묶음일 뿐 DB 그룹이 아님**을 코드 주석과 문서에 명시
- [ ] SYSTEM 탭은 카테고리 계층 없이 지시문 1건만 다룰 것

### B-08 · 시스템 지시문 버전 보관 — P2
`prompt_system_prompts`는 `code` 단위로 1건만 저장하고 이전 버전을 남기지 않습니다. 되돌리기가 성립하지 않아 화면에서도 버튼을 비활성 처리했습니다.

- [ ] `version` 컬럼 + 이력 행 유지로 변경하면 `7a`의 되돌리기와 변경 이력을 살릴 수 있음
- [ ] 하지 않을 경우 화면의 비활성 상태를 그대로 유지

---

## C · 화면만 구현하면 되는 것 (백엔드 변경 없음)

아래는 API와 테이블이 이미 준비되어 있습니다. 프론트 구현만 하십시오. **이 목록은 "백엔드 준비 상태" 참고용으로 남기고, 실제 화면 구현 순서·방식은 아래 E 절을 따르십시오.**

- [x] **C-01 `2b` 프롬프트 경고 표시** — `generate_prompt`가 이미 용어 검증·관계 적용·`prompt_rules` 평가·Scene 검증을 거쳐 `{code, message, severity}` 배열을 반환하고 `warnings_json`에 저장합니다. 화면은 이를 심각도별로 나눠 그리기만 하면 됩니다. — *경고 심각도별 그룹핑 로직은 완료(커밋 `9535b9f`, `e048f72`)했으나, 구버전 `PromptBuilderModal`(기존 dark 테마) 안에 구현되어 README Design Tokens를 적용하지 않음. 신규 `2b` 화면(E-02)에서 로직만 재사용하고 UI는 새로 그려야 함. 참고 — 이 커밋은 error 심각도일 때 Apply 버튼을 실제로 비활성화하는 동작을 TASKS.md 문구("그리기만 하면 됩니다")보다 넓게 추가했음(라벨-동작 불일치 방지 목적) — E-02 재구현 시 이 동작도 유지.*
- [x] **C-02 `2c` 취소 상태** — `POST /api/jobs/{id}/cancel` 존재. 요청 후 UI 잠금은 클라이언트 상태. — *E-02(`851dac4`)에서 `Create2cScreen` 구현으로 반영.*
- [x] **C-03 `3a` 삭제** — `POST /api/history/{task_id}/delete` 존재. — *E-03(`9e6e7f8`)에서 `Create3aScreen`의 삭제 모달로 반영.*
- [x] **C-04 `3f` `3c` Run 상세** — `GET /jobs/{id}/prompts`, `PATCH …/quality`, `PATCH …/review`, `review_status`·`review_flags_json` 컬럼 존재. — *E-03(금번 세션, 커밋 예정)에서 `Create3RunDetailScreen` 구현으로 반영.*
- [x] **C-05 `4c` 재사용** — `GET /api/prompts/reusable` (keyword·workflowId·minRating·reviewedOnly·reuseEligible·limit) 존재. — *E-03(금번 세션, 커밋 예정)에서 `Create4cScreen` 구현으로 반영.*
- [ ] **C-06 `7a` 시스템 프롬프트** — `GET/PUT /api/prompts/system-prompt` 존재.
- [ ] **C-07 `7b` 기능 리소스 매핑** — `GET /api/admin/permissions`가 roles·permissions·resources를 함께 반환. 조회 전용 화면.
- [ ] **C-08 `7c` 사용자 상세** — `PUT /admin/users/{id}`, `POST …/reset-password`, `POST …/deactivate`, `user_permissions` 테이블 존재.
- [ ] **C-09 `7g` 403·401·오류** — 라우트 가드와 응답 처리는 이미 있음. 화면만 필요.
- [x] **C-10 `2e` 세그먼트 설정** — `GET /api/segment-defaults`, `/workflows/{id}/segment-defaults` 존재. — *E-02(`8ac0c7a`)에서 `Create2eScreen` 구현으로 반영.*
- [ ] **C-11 `6c` `5b` 상태·Pod** — `/system/status`, `/runpod/connection`, `/admin/sandbox-pod` 존재.
- [ ] **C-12 `6d` 메타데이터** — `/metadata/status`, `/models`, `/rebuild` 존재.

---

## D · 결정 완료 · 그에 따른 작업

아래 3건은 결정되었습니다. 재론하지 말고 그대로 구현하십시오.

### D-01 · 리포트·구성 프리셋 — **유지하되 연결하지 않음** — **완료** (커밋 `b82a9c7`)
`POST/GET /api/reports`, `/api/configs`와 `reports`·`config_snapshots` 테이블은 그대로 둡니다. 화면은 만들지 않습니다.

- [x] 엔드포인트·테이블·서비스 코드를 **삭제하지 마십시오**
- [x] 프론트에서 이 API를 호출하는 코드가 있으면 제거 (`client.ts` 포함) — *`client.ts`에 reports/configs 호출 코드 없음을 grep으로 확인(원래도 없었음).*
- [x] 라우터 상단에 미연결 상태임을 주석으로 남길 것 — 예: `# UI 미연결 · 외부 연동 및 향후 화면용으로 유지 (2026-08 결정)`
- [ ] 화면 `7b` 리소스 매핑에서는 API로만 표시하고 SCREEN 행을 만들지 않음 — *`7b` 화면 자체가 아직 미착수(C-07/E-04)라 확인 불가. 해당 화면 구현 시점에 재확인.*

### D-02 · 카탈로그 조회 엔드포인트 — **재점검 결과 조치 불필요**
결정 당시 `GET /api/admin/prompt-catalog`가 중복 존재한다고 보았으나, **2026-08-10 재점검 결과 그 엔드포인트는 저장소에 없습니다.** `backend/app/api/v1/admin.py`에는 users·permissions·roles·workflows만 있습니다.

카탈로그 조회는 `GET /api/prompts/catalog` 하나뿐이고, 이미 `prompts:build` `prompts:reuse` `prompt-catalog:read` `prompt-catalog:write` 중 아무거나 있으면 통과하도록 `require_any_permission`으로 열려 있습니다. 생성 화면과 관리자 화면이 같은 엔드포인트를 써도 됩니다.

- [x] 조치 불필요 — 화면 `4e` `3d` `4b`는 `GET /api/prompts/catalog`를 호출
- [x] 프론트에 `admin/prompt-catalog` 문자열이 남아 있는지만 확인하고, 있으면 제거 — *grep 결과 없음, 조치 불필요.*

### D-03 · 이력 저장소 — **DB 방식으로 통일** — **완료** (커밋 `2d8705f`)
이력 조회·삭제가 `json_repository`와 `db_adapter` 양쪽에 있습니다. **DB를 운영 기준으로 합니다.**

- [x] 이력 조회·삭제·상세 경로가 모두 `db_adapter`를 타도록 라우터 정리
- [x] `json_repository`의 이력 관련 함수는 제거하거나, 남긴다면 마이그레이션 도구 전용임을 주석으로 명시
- [x] JSON 파일에만 있고 DB에 없는 과거 이력이 있는지 확인하고, 있으면 일회성 이관 스크립트 작성 — *`data/history.json`(23건) vs `workflow_tasks`(25건) 직접 대조, JSON에만 있고 DB에 없는 항목 0건 확인. 기존 `scripts/migrate_json_to_db.py`가 이미 존재·정상 동작해 신규 스크립트 불필요.*
- [ ] 페이지네이션(B-01)과 soft delete(B-05)는 DB 경로에만 구현 — **이 항목이 두 작업의 선행 조건입니다** — *B-01(페이지네이션)은 DB 경로로 구현 완료. B-05(soft delete)는 미착수라 이 항목은 B-05 완료 후 재확인 필요.*

완료 기준 — 이력 화면의 어떤 동작도 JSON 파일을 읽거나 쓰지 않는다. — *스모크 테스트로 확인(커밋 메시지 참조). 단, 이력 "화면" 자체는 구버전 UI라 신규 `3a` 화면 구현(E-03) 후 재검증 필요.*

---

## E · 화면 재구축 — 신규 디자인 토큰·공통 레이아웃·업무 흐름 기준 구현

**여기가 이 작업의 본체입니다.** A~D는 화면이 딛고 설 API·DB·권한 정합을 맞추는 선행 작업이었고, 그중 착수 대상이던 것(S-01·D-01·D-02·D-03·B-06·B-02·B-03·B-01·B-04·C-01 일부)은 위에서 보듯 이미 처리되었습니다. 그러나 **실제 화면은 여전히 구버전 `frontend/src/main.tsx`(단일 파일, 기존 dark 테마, 기능 기준 라우팅)이고, README가 요구하는 "부분 수정이 아닌 전면 재구축"은 아직 시작되지 않았습니다.** C-01/B-01/B-04에서 이미 만든 로직(경고 그룹핑, 페이지네이션, 실행 모드 판단)은 재사용하되, 그 로직이 지금 얹혀 있는 구버전 UI는 폐기 대상입니다.

### E-00 · 디자인 토큰 도입 — P0 — **완료** (커밋 `8602b95` 및 후속 화면 커밋에 포함)
- [x] README Design Tokens(배경/텍스트/경계/액센트/경고/위험 색상, IBM Plex Sans·Roboto Mono, 라운드값, 사이드바 212px 등)를 `frontend/src/styles.css`에 단일 소스(CSS 변수)로 도입 — *`--v3-*` 접두 변수로 도입, `styles.css` 최상단에 정의.*
- [x] 코드베이스에 이미 동등 역할의 토큰이 있으면 그쪽을 우선하고, 충돌하는 값은 표로 정리해 결정 요청 — *충돌 없음(신규 네임스페이스라 대조 불필요).*
- [x] 구버전 dark 테마 변수와 신규 토큰이 공존하는 과도기 동안 서로 새지 않도록 네임스페이스 분리 — *`--v3-*` 전용 접두로 분리, 구버전 변수와 클래스 겹침 없음.*

### E-01 · 공통 레이아웃 컴포넌트 — P0 (E-00 선행) — **완료** (커밋 `8602b95`)
- [x] `frontend/src/components/`에 사이드바 212px + 헤더 + 본문 그리드 + 우측 패널을 담는 레이아웃 컴포넌트 신설 — 화면마다 새로 짜지 않고 전 화면이 공유 — *`frontend/src/components/AppShell.tsx` 신설.*
- [x] 권한 없는 메뉴는 사이드바에서 숨기고, 직접 URL 진입만 `7g`(C-09) 403 화면에 도달하도록 가드 위치 결정 — *`ROUTE_REQUIRED_PERMISSION`/`routeAccessGranted()`(main.tsx)로 라우트별 권한 가드 구현. `7g` 전용 화면은 아직 없어 임시 `AccessDeniedModal`로 대체(E-05에서 정식 화면으로 교체 필요).*
- [x] `router.ts`를 업무 흐름(S1~S5) 기준 라우트로 재설계(현재는 기능 기준: login/studio/history/status/metadata/manual/admin) — *`StudioRoute`를 `"flow.screen"` 리터럴 유니온으로 전면 재작성, 구버전 경로 호환은 `LEGACY_LAST_SEGMENT_ROUTE`로 유지.*

### E-02 · `2 Create` 흐름 (핵심 흐름) — P0 — **완료** (커밋 `8602b95`, `cc85438`, `8ac0c7a`, `851dac4`)
순서: `2a`→`2b`→`2e`→`2f`→`2c`→`2d`
- [x] `2a` 이미지 로드 — 워크플로 선택 + 키프레임 업로드 — *커밋 `8602b95`.*
- [x] `2b` 프롬프트 구성 — **C-01 경고 그룹핑 로직(심각도별 분류, BLOCK 시 Apply 비활성) 재사용, UI는 신규 토큰·레이아웃으로 재구현.** 경고는 좌측 본문 상단 스트립에 모으고 우측 패널로 분산하지 않음(README 지시) — *커밋 `cc85438`.*
- [x] `2e` 세그먼트 설정 (C-10) — *커밋 `8ac0c7a`.*
- [x] `2f` 실행 전 확인 — 제출 payload 확인 후 Run — *커밋 `851dac4`.*
- [x] `2c` 진행 — 상태 인포그래픽 + 로그 + 취소 요청(Cancelling) 상태(C-02) — *커밋 `851dac4`.*
- [x] `2d` 결과 — Final 병합본과 구간 검수본 — *커밋 `851dac4`.*

### E-03 · `3 Review` 흐름 — P1 — **`5c` 제외 완료** (커밋 `9e6e7f8` 및 금번 세션 미커밋분)
- [x] `3a` 작업 이력 — **B-01 페이지네이션 로직(20/50, 총 건수·범위 표시) 재사용**, 삭제(C-03) 포함 — *커밋 `9e6e7f8`.*
- [x] `3f`/`3c` Run 상세 — **B-02 평가 로직(task_prompts/prompt_feedback 역할 분리) 재사용**(C-04) — *`Create3RunDetailScreen`으로 완료/실패 화면 통합 구현, 평가 카드는 `V3PromptReviewGroup`으로 분리. 아직 커밋 전(다음 커밋에 포함 예정).*
- [x] `4c` 프롬프트 재사용 (C-05) — *`Create4cScreen` 구현. 아직 커밋 전(다음 커밋에 포함 예정).*
- [x] `5a` 자산 — A-01(자산 목록 API) 선행 필요, API 완성 후 착수 — *A-01 API·화면 모두 완료(`Create5aScreen`). 아직 커밋 전.*
- [ ] `5c` 컬렉션 — *의도적으로 범위 밖. A-02(컬렉션 테이블·API)가 저장소에 전혀 없어(`collections`/`collection_items` 마이그레이션 없음, `GET/POST /api/collections` 없음) 화면을 만들면 전부 가짜 데이터가 됨 — 원칙 위반이라 보류. A-02 착수 후 재개.*

### E-04 · `4 Admin` 흐름 — P1 — **진행 중** (`7a`·`6c` 완료)
구버전 `AdminConsoleModal`(탭형 단일 모달, main.tsx)이 users/roles/catalog/workflows/sandbox를 이미 다 구현해 두었고, `StatusModal`(6c)·`MetadataModal`(6d)·`SystemPromptEditor`(7a 원형)도 각각 독립 라우트/패널로 존재했다. E-04는 이 로직들을 유지한 채 화면만 `AppShell` 기반 v3 화면으로 하나씩 옮기는 작업이다 — 새 API를 만들 필요가 거의 없다(4b 제외).
- [ ] `4e` 카탈로그 계층, `3d` 용어 관리 — B-06 신형 계층 완료로 착수 가능. 기존 `PromptCatalogAdminContent`(main.tsx) 로직 재사용, 화면 2개로 분리 예정.
- [ ] `4b` Negative 기본값 — *기존 admin UI 자체가 없음(신규 설계 필요). 4e/3d 완료 후 그 용어 선택 컴포넌트를 재사용해 진행 예정.*
- [x] `7a` 시스템 프롬프트 (C-06) — *`Create7aScreen` 구현. `SystemPromptEditor`/2b의 systemPrompt 패널과 완전히 같은 상태(`promptSystemPrompt`/`promptSystemPromptText`)를 공유 — 어느 화면에서 고쳐도 같은 전역 레코드(`prompt_system_prompts`)에 반영됨(B-08 미착수라 버전 이력은 없음).*
- [ ] `4d`/`4a` 워크플로 정의 — 기존 `AdminConsoleModal` Workflows 탭 로직(등록/활성화/비활성화) 재사용 예정.
- [ ] `6d` 메타데이터 (C-12) — 기존 `MetadataModal` 로직 재사용 예정.
- [ ] `3b` 역할×권한 매트릭스 — 기존 `AdminConsoleModal` Permissions 탭(역할 목록 + 권한 토글 그리드) 재사용 예정.
- [ ] `7b` 기능 리소스 매핑 (C-07) — D-01의 "SCREEN 행 만들지 않음" 반영. 현재 3b와 같은 탭 안에 표만 있음 — 별도 화면으로 분리 예정.
- [ ] `3e` 사용자 목록, `7c` 사용자 상세 (C-08) — 기존 Users 탭 로직 재사용하되, `client.ts`에 이미 있는 `resetAdminUserPassword`/`deactivateAdminUser`가 지금까지 어디서도 호출되지 않고 있어(미사용) 이번에 처음 UI에 연결해야 함.
- [x] `6c` 시스템 상태 (C-11) — *`Create6cScreen` 구현. `StatusModal`/`StatusCard`와 동일한 판정식(dry-run/ok 계산) 그대로 이관, 카드 7장 전부 실제 헬스체크 응답 필드. 구버전 `StatusModal` 오픈 로직(`statusModalOpen`)은 이제 항상 false로 죽은 코드(E-06 정리 대상).*
- [ ] `5b` Sandbox Pod (C-11) — 기존 Sandbox 탭 로직(status/start/stop, `SandboxPodConfirmModal`) 재사용 예정.
- [ ] `미구현` 배지 영역(감사 로그, 변경 이력, 접근 이력, Pod 제어 이력)은 A-04 전까지 임의 데이터로 채우지 않음 — *각 화면 이관 시점마다 확인, 아직 전 화면 완료 전이라 최종 확인은 E-04 종료 시.*

E-04 진행 중 `AppShell.tsx`의 `ADMIN_NAV_ITEMS`에 `adminStatus`(6c)·`adminMetadata`(6d) 두 항목을 추가했다 — design_handoff 원본은 이 둘을 6항목 Admin 사이드바가 아닌 별도 상단 nav로 그리지만, AppShell이 area를 `generate`/`admin` 두 가지만 지원하는 현재 구조에서는 관리 기능에 가까운 이 둘을 ADMIN 영역에 편입하는 편이 화면 골격 중복을 피할 수 있다고 판단했다. 화면 내용·API·권한은 design_handoff 그대로다.

### E-05 · `1 Access` 흐름 — P2
- [ ] `6a` 로그인
- [ ] `7g` 403/401/오류 (C-09)
- [ ] `6b` 사용자 매뉴얼
- [ ] `6e` 알림 — **A-03 방식 결정 전 착수 금지**

### E-06 · 구버전 제거 — 각 흐름 이관 완료마다 즉시
- [ ] 대체된 구버전 컴포넌트·모달을 `main.tsx`에서 실제로 삭제(죽은 코드로 남기지 않음)
- [ ] `main.tsx`가 계속 단일 거대 파일로 남지 않도록 신규 컴포넌트를 파일 단위로 분리
- [ ] 전 화면을 나란히 열어 사이드바 폭·헤더 높이·색·간격 일관성 확인

---

## 권장 순서

1. ~~**S-01 · D-03 · D-02 · D-01**~~ — **완료.** 코드 정렬과 정리, 다른 작업의 토대.
2. ~~**B-06**~~ — **완료(1~3단계, 4단계 컬럼 정리까지).** 카탈로그 관련 화면 전부가 여기에 막혀 있었으나 이제 해제됨.
3. ~~**B-02 · B-03 · B-01 · B-04**~~ — **완료.** 로직은 끝났고 화면은 E 절에서 이관.
4. ~~**E-00 → E-01 → E-02 → E-03**~~ — **완료 (`5c`만 A-02 대기로 제외).** 다음은 **E-04 → E-05 → E-06**. C-01~C-12는 이 단계에 흡수됨.
5. **A-01 → A-04 → B-05** — 신규 개발.
6. **A-02 · A-03 · A-06 · B-08** — 후순위.

의존 관계 — `D-03` → `B-01`·`B-05` / `B-06` → `E-02`·`E-04`의 카탈로그 화면 / `A-04` → `B-05`의 삭제 기록 / `E-00`·`E-01` → E-02~E-06 전체
