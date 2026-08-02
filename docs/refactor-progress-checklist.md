# DOBEDUB STUDIO v3 리팩터링 진행 체크리스트

작성일: 2026-08-02  
기준 문서: `docs/refactor-and-prompt-llm-advancement-plan.md`

## 운영 원칙

- ECS 배포는 하지 않는다.
- 각 단계는 로컬 검증을 통과한 뒤 다음 단계로 진행한다.
- 가능한 단계마다 자동 smoke test를 추가하거나 갱신한다.
- 기존 monolith 앱의 동작을 먼저 보존한 뒤 구조를 나눈다.
- GitHub 동기화는 사용자 지시 또는 단계 완료 보고 시점에만 수행한다.

## Step 0. 기준선 고정 및 회귀 테스트

- [x] v3 독립 작업 폴더 생성
- [x] v3 GitHub 저장소 동기화
- [x] 불필요한 `Workflow2/` 제거
- [x] 로컬 smoke test 스크립트 추가
- [x] 현재 monolith API 기준 smoke test 통과
- [x] 기존 주요 기능별 수동 확인 항목 문서화

로컬 확인 명령:

```bash
python3 scripts/local_smoke_check.py
python3 -m py_compile server.py
node --check src/app.js
```

## Step 1. FastAPI 백엔드 skeleton

- [x] `backend/` 디렉토리 생성
- [x] FastAPI 앱 skeleton 추가
- [x] config/settings 모듈 추가
- [x] `/api/v1/health` 구현
- [x] 기존 monolith와 병렬 실행 가능하게 구성
- [x] smoke test에 FastAPI health 확인 추가

로컬 확인 기준:

- monolith smoke test 통과
- FastAPI `/api/v1/health` 응답 확인
- 기존 UI 파일은 아직 변경하지 않음

로컬 확인 명령:

```bash
python3 scripts/fastapi_smoke_check.py
python3 scripts/local_smoke_check.py
python3 -m py_compile server.py scripts/local_smoke_check.py scripts/fastapi_smoke_check.py backend/app/main.py
node --check src/app.js
```

## Step 2. 서비스 계층 추출

- [x] workflow 조회 service wrapper 추가
- [x] segment defaults 조회 service wrapper 추가
- [x] metadata 조회 service wrapper 추가
- [x] FastAPI workflow/metadata 조회 endpoint 추가
- [ ] workflow parser 추출
- [ ] segment defaults loader 추출
- [ ] metadata loader 추출
- [ ] runpod client 추출
- [ ] asset storage 추출
- [ ] monolith와 FastAPI가 같은 service 함수를 재사용하도록 조정

로컬 확인 기준:

- monolith smoke test 통과
- FastAPI workflow endpoint 최소 1개 통과

## Step 3. MySQL 도입 준비

- [ ] SQLAlchemy/Alembic 설정
- [ ] MySQL schema 초안 migration 작성
- [ ] JSON repository adapter와 DB repository adapter 인터페이스 분리
- [ ] `docker-compose.dev.yml`에 MySQL 추가
- [ ] migration dry-run 또는 SQLite 대체 검증 전략 확정

로컬 확인 기준:

- migration 생성/검증
- 기존 JSON adapter 동작 유지

## Step 4. React 프론트 skeleton

- [ ] `frontend/` Vite + React + TypeScript 생성
- [ ] 라우터 구성
- [ ] API client 구성
- [ ] Login/Studio shell 구현
- [ ] 기존 vanilla UI와 병렬 유지

로컬 확인 기준:

- React dev server 실행
- `/login`, `/studio` 렌더 확인
- 기존 monolith UI 동작 유지

## Step 5. Prompt DB 및 Prompt Builder

- [ ] prompt category/term schema 작성
- [ ] seed data 작성
- [ ] prompt builder scene JSON 생성 API
- [ ] positive/negative 직접 입력 방식과 병행

로컬 확인 기준:

- 카테고리/키워드 조회 가능
- scene JSON 생성 가능

## Step 6. LLM 프롬프트 생성 연동

- [ ] LLM endpoint 설정 분리
- [ ] prompt generation API 추가
- [ ] JSON Schema 검증
- [ ] 생성/수정/평가 이력 저장
- [ ] Studio prompt field 적용 흐름 구현

로컬 확인 기준:

- mock LLM provider로 deterministic output 생성
- 실제 RunPod vLLM endpoint는 별도 수동 확인 후 활성화
