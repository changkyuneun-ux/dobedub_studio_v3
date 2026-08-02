# ComfyUI Video Studio App

RunPod Serverless에서 실행되는 ComfyUI Export(API) 워크플로우를 사내 사용자가 웹 UI로 실행하기 위한 새 프로젝트입니다.

현재 버전은 프론트 UI와 로컬 API 서버가 함께 동작하는 구현입니다. API 서버는 프로젝트 내부 `workflows/`의 ComfyUI Export(API) JSON을 읽어 workflow/segment schema를 만들고, `.env` 설정에 따라 dry-run 또는 실제 RunPod Serverless endpoint로 작업을 제출합니다.

## 실행

권장 실행:

```bash
cd comfyui-video-studio-app
python3 server.py
```

브라우저에서 접속:

```text
http://127.0.0.1:8787
```

정적 UI만 확인하려면 아래 파일을 직접 열 수도 있습니다. 이 경우 API 호출은 fallback mock 데이터로 동작합니다.

```text
index.html
```

별도 패키지 설치 없이 Python 표준 라이브러리만으로 동작합니다.

## 포함 화면

- 로그인 화면
  - ID, Password, Name 필수 입력
  - 외부 SSO 없음
- 메인 대시보드
  - workflow 선택
  - workflow 입력 이미지 수에 맞춘 고정 keyframe upload 슬롯
  - 다중 이미지 선택 시 슬롯 순서대로 자동 배치
  - 슬롯별 이미지 미리보기, 교체, 삭제
  - segment 선택
  - segment별 positive/negative prompt 편집
  - FPS, Frames, Steps, CFG Scale, Motion Shift, Seed 설정
  - generation progress mock
  - output preview mock
- 작업이력 모달
  - 작업 리스트
  - 작업 상세
  - node config
  - output preview

## 구현된 API

- `GET /api/health`
- `GET /api/system/status`
- `GET /api/runpod/connection`
- `GET /api/workflows`
- `GET /api/workflows/{workflowId}/schema`
- `POST /api/auth/login`
- `POST /api/uploads`
- `POST /api/jobs`
- `GET /api/jobs/{taskId}`
- `GET /api/history`
- `GET /api/configs`
- `POST /api/configs`
- `POST /api/reports`
- `GET /api/reports/{reportId}`
- `GET /api/files/{assetId}`

## 환경변수

서버는 앱 폴더의 `.env` 파일을 자동으로 읽습니다. 먼저 샘플을 복사한 뒤 실제 값을 입력합니다.

```bash
cp .env.example .env
```

```bash
WORKFLOWS_DIR=./workflows
STUDIO_DATA_DIR=./data
OUTPUTS_DIR=./data/outputs
RUNPOD_DRY_RUN=0
RUNPOD_API_KEY=your_runpod_api_key
RUNPOD_ENDPOINT_ID=your_runpod_endpoint_id
PORT=8787
```

실제 RunPod Serverless에 제출하려면 `RUNPOD_DRY_RUN=0`으로 실행하고 `RUNPOD_API_KEY`, `RUNPOD_ENDPOINT_ID`를 설정합니다. 이때 서버는 프로젝트 내부 workflow JSON을 패치하고 업로드 이미지를 RunPod `images` payload로 변환한 뒤 `/run`과 `/status/{jobId}`를 사용합니다.

실행 후 상단 `Check Status` 모달에서 `Test RunPod`를 누르면 실제 작업을 생성하지 않고 RunPod `/health`만 호출해 endpoint 접근, worker 상태, queue 상태를 확인합니다.

## 다음 구현 단계

1. 실제 RunPod endpoint에서 workflow별 smoke test를 수행하고 paramconfig 매핑을 검증합니다.
2. RunPod handler output 형식이 `videos`/`images` base64 또는 `s3_url` 중 어느 쪽인지 확정해 preview 정책을 고정합니다.
3. 결과 파일 저장은 초기에는 `OUTPUTS_DIR`, 운영에서는 EFS 또는 S3를 사용합니다.
4. 작업이력은 현재 `data/history.json`에서 시작하고, 운영에서는 DB로 이전합니다.

## 참조 문서

- `../docs/comfyui-video-studio-ui-design.md`
- `../docs/serverless-comfyui-app-implementation-design.md`
- `./workflows`
