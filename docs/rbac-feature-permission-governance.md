# DOBEDUB STUDIO Role/Permission/Feature Governance

작성일: 2026-08-05
대상: `comfyui-video-studio-app-v3`

## 1. 목적

기능 목록이 변경될 때 사용자 권한, 역할 그룹, 메뉴 노출, 버튼 활성화, API 접근 제어가 함께 정합성을 유지해야 한다. 현재 v3는 `roles`, `permissions`, `role_permissions`, `user_permissions`, `ui_permission_resources`를 기준으로 기능-권한-역할-UI 매핑을 관리한다.

이 문서는 다음 원칙을 기준으로 한다.

- Role은 기본 permission group이다.
- 사용자는 하나의 Role을 기본으로 가진다.
- 사용자별 Permission은 Role에 없는 예외적 추가 권한만 선택한다.
- 화면 메뉴/버튼은 Role이 아니라 effective permission 기준으로 노출/활성화한다.
- Frontend 제어는 UX이며, Backend API에서도 동일 permission을 강제한다.
- 기능 목록 변경은 반드시 feature/resource catalog 변경으로 기록하고, 필요한 permission 및 role mapping을 같이 검토한다.

## 2. 현재 구조 진단

현재 구조:

- `users.role`: `SUPER_ADMIN`, `ADMIN`, `OPERATOR`, `VIEWER` 문자열
- `roles`, `permissions`, `role_permissions`, `user_permissions`, `ui_permission_resources`: RBAC 원장
- `users.permissions_json`: 과거 호환용 legacy 추가 권한 저장소. 신규 운영은 `user_permissions`를 기준으로 한다.
- Frontend permission option은 backend permission catalog와 label을 맞춰 유지한다.
- API route는 `require_permission()` 또는 `require_any_permission()`으로 기능별 권한을 검사한다.
- TopBar 메뉴, 주요 action button, History/Admin 내부 action button은 effective permission 기준으로 표시/활성화한다.

남은 문제:

- 인증은 DB 로그인 후 발급되는 JWT를 `Authorization: Bearer <JWT>` 헤더로 전달한다. `X-User-*` 헤더는 신뢰하지 않으며, 역할과 권한은 매 요청마다 DB의 활성 사용자 및 RBAC 매핑으로 계산한다.
- UI resource mapping은 `resource -> permission` 단일 매핑이다. Admin Console처럼 여러 권한 중 하나로 진입하는 영역은 하위 탭별 resource로 분리해 관리한다.
- 기능 제거/이름 변경 시 오래된 permission/resource가 남지 않도록 smoke와 운영 점검이 필요하다.

## 3. 권장 데이터 모델

### 3.1 역할

`roles`

| 컬럼 | 설명 |
|---|---|
| `id` | 내부 PK |
| `code` | `SUPER_ADMIN`, `ADMIN`, `OPERATOR`, `VIEWER` |
| `name` | 표시명 |
| `description` | 설명 |
| `level` | 권한 수준 정렬용 숫자 |
| `is_system` | 기본 제공 역할 여부 |
| `is_active` | 사용 여부 |
| `sort_order` | 표시 순서 |
| `created_at`, `updated_at` | 감사 정보 |

### 3.2 권한

`permissions`

| 컬럼 | 설명 |
|---|---|
| `id` | 내부 PK |
| `code` | `jobs:run`, `metadata:read` 등 |
| `domain` | `jobs`, `history`, `prompts`, `admin` 등 |
| `action` | `read`, `write`, `run`, `cancel`, `review` 등 |
| `name` | 표시명 |
| `description` | 설명 |
| `is_system` | 기본 제공 권한 여부 |
| `is_active` | 사용 여부 |
| `sort_order` | 표시 순서 |

### 3.3 역할-권한 매핑

`role_permissions`

| 컬럼 | 설명 |
|---|---|
| `role_id` | 역할 |
| `permission_id` | 권한 |
| `created_at` | 생성일 |

Role 기본 권한은 이 테이블로만 관리한다.

### 3.4 사용자 추가 권한

`user_permissions`

| 컬럼 | 설명 |
|---|---|
| `user_id` | 사용자 |
| `permission_id` | 추가 권한 |
| `grant_type` | 우선 `ALLOW`만 사용 |
| `note` | 예외 부여 사유 |
| `created_at` | 생성일 |

초기 버전에서는 `DENY`를 두지 않는다. Deny precedence는 운영자가 이해하기 어렵고 디버깅 비용이 크기 때문이다.

### 3.5 기능/메뉴/액션 리소스 매핑

`ui_permission_resources`

| 컬럼 | 설명 |
|---|---|
| `id` | 내부 PK |
| `resource_type` | `MENU`, `ACTION`, `API` |
| `resource_key` | `top.history`, `action.generate_video` 등 |
| `label` | 표시명 |
| `required_permission_code` | 필요한 permission |
| `route_path` | 연결 route 또는 API path |
| `method` | API method, UI resource는 nullable |
| `is_active` | 사용 여부 |
| `sort_order` | 표시 순서 |

이 테이블은 기능 목록 변경 시 가장 먼저 확인하는 원장이다.

## 4. 초기 권한 카탈로그

| Permission | 목적 |
|---|---|
| `admin:*` | 전체 관리자 권한 |
| `users:read` | 사용자 목록/상세 조회 |
| `users:write` | 사용자 등록/수정/상태 변경 |
| `roles:read` | 역할/권한 그룹 조회 |
| `roles:write` | 역할별 권한 구성 변경 |
| `workflows:read` | 워크플로우 조회 |
| `workflows:write` | 워크플로우 등록/수정 |
| `workflows:activate` | 워크플로우 활성화/비활성화 |
| `prompt-catalog:read` | Prompt Catalog 조회 |
| `prompt-catalog:write` | Prompt Catalog 관리 |
| `prompts:build` | Prompt Builder 사용 |
| `prompts:reuse` | 재사용 프롬프트 검색/적용 |
| `prompts:review` | 프롬프트 품질 등급/코멘트/재사용 여부 관리 |
| `jobs:run` | 영상 생성 작업 실행 |
| `jobs:cancel` | 생성 작업 취소 |
| `history:read` | 작업 이력 조회 |
| `history:delete` | 작업/asset 삭제 |
| `metadata:read` | Workflow metadata 조회 |
| `metadata:rebuild` | Workflow metadata 재생성 |
| `system:read` | ComfyUI/Qwen/DB 상태 조회 |
| `manual:read` | 사용자 매뉴얼 조회 |

## 5. 초기 역할 기본 권한

| Role | 기본 권한 |
|---|---|
| `SUPER_ADMIN` | `admin:*` |
| `ADMIN` | `users:*`, `roles:*`, `workflows:*`, `prompt-catalog:*`, `prompts:review`, `history:*`, `metadata:*`, `system:read`, `manual:read` |
| `OPERATOR` | `workflows:read`, `jobs:run`, `jobs:cancel`, `history:read`, `prompts:build`, `prompts:reuse`, `prompts:review`, `metadata:read`, `system:read`, `manual:read` |
| `VIEWER` | `workflows:read`, `history:read`, `metadata:read`, `system:read`, `manual:read` |

Wildcard는 내부 계산에서만 지원한다. UI에서는 가능한 한 개별 permission을 표시한다.

## 6. 메뉴/기능 매핑 기준

| 메뉴/기능 | Required Permission |
|---|---|
| History/Saved Videos | `history:read` |
| Check Status | `system:read` |
| Metadata View | `metadata:read` |
| Rebuild Metadata | `metadata:rebuild` |
| User Manual | `manual:read` |
| Admin Console 진입 | `users:read` 또는 `roles:read` 또는 `workflows:write` 또는 `workflows:activate` 또는 `prompt-catalog:write` |
| Admin - Users 탭 | `users:read` |
| Admin - User 저장 | `users:write` |
| Admin - Roles/Permissions 탭 | `roles:read` |
| Admin - Role 권한 저장 | `roles:write` |
| Admin - Workflows 탭 | `workflows:read` |
| Workflow 등록/수정 | `workflows:write` |
| Workflow 활성화/비활성화 | `workflows:activate` |
| Admin - Prompt Catalog 탭 | `prompt-catalog:read` |
| Prompt Catalog 저장/비활성화 | `prompt-catalog:write` |
| Prompt Builder | `prompts:build` |
| Prompt Reuse | `prompts:reuse` |
| Prompt Review 저장 | `prompts:review` |
| Generate Video | `jobs:run` |
| Cancel Generation | `jobs:cancel` |
| 작업 삭제 | `history:delete` |

## 7. 내부 처리 로직

### 7.1 Effective Permission 계산

```text
effective_permissions(user)
  = role_permissions(user.role)
  + user_extra_permissions(user.id)
```

권한 검사:

```text
has_permission(user, required)
  true if admin:* exists
  true if exact required exists
  true if domain:* exists
  false otherwise
```

예:

- `admin:*`은 모든 권한 허용
- `workflows:*`은 `workflows:read`, `workflows:write`, `workflows:activate` 허용
- `workflows:read`은 `workflows:write`를 허용하지 않음

### 7.2 Backend Guard

각 API는 다음과 같은 dependency를 사용한다.

```python
require_permission("users:write")
require_permission("jobs:run")
require_permission("metadata:rebuild")
```

Frontend에서 버튼을 숨겨도 API는 반드시 backend permission으로 다시 검사한다.

### 7.3 Frontend Guard

Frontend는 backend `/api/auth/me` 또는 `/api/admin/permissions/effective`에서 받은 effective permissions로 UI를 제어한다.

```text
can("history:read") -> History button 표시
can("jobs:run") -> Generate Video 활성화
can("roles:write") -> Role 권한 저장 버튼 활성화
```

## 8. 관리 메뉴 구성

Admin Console에 다음 탭을 추가/정리한다.

1. `Users`
   - 사용자 목록
   - 사용자 상세/수정
   - Role 선택
   - Role 기본 권한 읽기 전용 표시
   - 사용자 추가 권한 선택
   - Effective Permission 미리보기

2. `Roles & Permissions`
   - Role 목록
   - Role별 기본 권한 체크 관리
   - Permission catalog 조회
   - Feature resource mapping 조회

3. `Workflows`
   - 기존 workflow 관리

4. `Prompt Catalog`
   - 기존 Prompt Catalog 관리

초기에는 `Roles & Permissions`에서 시스템 permission의 삭제는 금지한다. 활성/비활성 또는 role mapping 변경만 허용한다.

## 9. 기능 변경 운영 절차

기능 추가 시:

1. 기능 key 정의: 예 `action.prompt_reuse_apply`
2. 필요한 permission 결정: 예 `prompts:reuse`
3. `ui_permission_resources`에 메뉴/버튼/API mapping 추가
4. 필요 시 `permissions`에 신규 permission 추가
5. 기본 role mapping 검토
6. frontend `can(...)` 적용
7. backend `require_permission(...)` 적용
8. smoke test에 role별 노출/비노출 케이스 추가

기능 삭제/이름 변경 시:

1. 연결된 `ui_permission_resources` 비활성화
2. 관련 permission이 더 이상 쓰이지 않는지 점검
3. role/user permission orphan 여부 점검
4. UI/API smoke 갱신

## 10. 구현 단계

### Phase A. 기준선 정리

- [x] Role/Permission/Feature Governance 문서 확정
- [x] 기존 hardcoded permission list를 backend seed catalog로 이동
- [x] 사용자 관리 UI에서 free text permission 입력 제거

### Phase B. DB/Alembic

- [x] `roles`
- [x] `permissions`
- [x] `role_permissions`
- [x] `user_permissions`
- [x] `ui_permission_resources`
- [x] seed migration 추가

### Phase C. Backend

- [x] effective permission service 추가
- [x] wildcard permission 검사 추가
- [x] admin role/permission catalog API 추가
- [x] 기존 `require_admin()`을 `require_permission()` 기반으로 점진 전환
- [x] 주요 API route별 guard 적용

### Phase D. Frontend

- [x] `can(permission)` helper 추가
- [x] TopBar 메뉴 guard 적용
- [x] 주요 action button guard 적용
- [x] History/Admin 내부 action guard 적용
- [x] Admin Console에 `Roles & Permissions` 탭 추가
- [x] User 관리 화면을 Role 기본 권한 + 추가 권한 선택 구조로 변경

### Phase E. 검증

- [x] role별 API 접근 smoke
- [x] role별 메뉴/버튼 노출 smoke
- [x] 기능 resource mapping 누락 검사 script
- [x] orphan permission 검사 script

## 11. 주의사항

- 로그인은 DB 사용자 권한 검증을 위해 활성화되어 있다. 개발 편의용 `DEV_USER` 상수는 fallback 용도로만 남긴다.
- Permission은 보안 경계이므로 frontend guard만으로 완료 처리하지 않는다.
- 사용자별 추가 권한은 운영 예외로만 사용한다. Role 설계가 계속 우선이다.
- Deny permission은 초기 도입하지 않는다.
