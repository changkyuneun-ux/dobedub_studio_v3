# API Integration Notes

이 문서는 정적 프론트 프로토타입을 실제 RunPod Serverless ComfyUI 실행 앱으로 연결할 때 필요한 API 경계를 정리한다.

## 1. 프로젝트 내부 리소스

앱 실행에 필요한 workflow 리소스는 프로젝트 내부에 포함한다.

```text
comfyui-video-studio-app/workflows
```

포함 대상:

- `*-key-frames.json`
- `*-key-frames.paramconfig.json`
- `README.md`

## 2. 필수 API

### POST /api/auth/login

ID, Password, Name을 검증하고 세션을 생성한다.

### GET /api/system/status

현재 실행 모드, RunPod 설정 여부, workflow 폴더, data/output 저장소 준비 상태를 반환한다.

### GET /api/runpod/connection

RunPod queue endpoint의 `/health`를 호출해 실제 endpoint 접근 가능 여부를 확인한다.
이 호출은 작업을 생성하지 않으며 worker idle/running 수와 queue 상태만 반환한다.

### GET /api/workflows

`workflows/*.json`을 읽고 workflow mode, keyframe count, segment count를 반환한다.

### GET /api/workflows/{workflowId}/schema

`workflow_utils.py`로 workflow JSON을 분석해 프론트가 그릴 segment schema를 반환한다.

### POST /api/uploads

이미지를 임시 저장하고 uploadId를 반환한다.

### POST /api/jobs

프론트의 workflowId, uploadId, segment prompts, node config를 받아 patched workflow를 만들고 RunPod `/run`에 제출한다.
`RUNPOD_DRY_RUN=1`이면 동일한 응답 구조로 로컬 시뮬레이션을 수행한다.

### GET /api/jobs/{taskId}

RunPod `/status/{jobId}`를 조회해 상태, 경과시간, 워커 요약, output readiness를 반환한다.
완료 상태에서는 RunPod output base64를 `OUTPUTS_DIR`에 저장하고 output asset을 history에 연결한다.

### GET /api/history

작업 목록을 반환한다. 초기에는 `outputs/작업내역.xlsx`를 읽어도 되고, 운영 단계에서는 DB를 권장한다.

### GET /api/configs

저장된 workflow/segment config snapshot 목록을 반환한다. 초기 구현은 `data/configs.json`을 사용한다.

### POST /api/configs

현재 편집 중인 config 또는 선택한 history item의 config snapshot을 내부 저장소에 저장한다.

### POST /api/reports

선택한 history item을 Markdown 리포트로 생성하고 reportId/downloadUrl을 반환한다.

### GET /api/reports/{reportId}

생성된 Markdown 리포트를 다운로드한다.

### GET /api/files/{assetId}

결과 MP4, 입력 이미지, output thumbnail을 다운로드한다. 실제 filesystem path는 브라우저에 직접 노출하지 않는다.

## 3. 프론트 연결 지점

`src/app.js`는 API 우선으로 동작하며, API 서버가 없거나 `file://`로 열면 fallback mock 데이터를 사용한다.

- workflow list -> `GET /api/workflows`
- system status -> `GET /api/system/status`
- runpod connection check -> `GET /api/runpod/connection`
- segment schema -> `GET /api/workflows/{id}/schema`
- job submit -> `POST /api/jobs`
- job progress -> `GET /api/jobs/{taskId}`
- history source -> `GET /api/history`
- config save/list -> `POST /api/configs`, `GET /api/configs`
- report generation -> `POST /api/reports`
- upload selected keyframe -> `POST /api/uploads`
- download action -> `GET /api/files/{assetId}`

## 4. RunPod Payload

```json
{
  "input": {
    "workflow": {},
    "images": [
      {
        "name": "kf1_image.png",
        "image": "base64..."
      }
    ]
  }
}
```

이 payload 형식은 기존 `RunPodComfyClient._build_payload()`와 동일하게 유지한다.

서버는 `workflows/<name>.paramconfig.json`이 있으면 UI의 `fps`, `frames`, `steps`, `cfgScale`,
`motionShift`, `seed` 값을 실제 ComfyUI 노드 input으로 반영한다.

## 5. 실제 RunPod 실행 조건

`.env`에서 아래 값을 설정한다.

```bash
RUNPOD_DRY_RUN=0
RUNPOD_API_KEY=...
RUNPOD_ENDPOINT_ID=...
```

실제 제출은 `POST /api/jobs`에서만 발생한다. `GET /api/runpod/connection`은 smoke test용 `/health` 호출이며 비용이 드는 job을 만들지 않는다.
