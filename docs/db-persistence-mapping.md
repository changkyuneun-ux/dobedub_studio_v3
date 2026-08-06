# DOBEDUB STUDIO v3 DB Persistence Mapping

작성일: 2026-08-02

이 문서는 현재 JSON 기반 저장 구조를 MySQL/RDS 기반 저장 구조로 전환하기 위한 필드 매핑 기준이다. 앱 런타임은 아직 JSON 저장소를 기본값으로 유지하며, DB adapter는 같은 API 반환 형태를 보존해야 한다.

## 전환 원칙

- 기존 프론트엔드가 기대하는 응답 필드명은 유지한다.
- `history.json`, `assets.json`, `configs.json`의 자유로운 dict 구조는 DB 컬럼과 JSON 컬럼을 함께 사용해 보존한다.
- 작업 이력 삭제 시 작업 row, 입력/출력 asset 연결, 관리 대상 파일 삭제가 함께 처리되어야 한다.
- RunPod job 실행 중 상태는 현재 메모리 `JOBS`에 있으므로, DB 전환 시 재시작 복구 정책을 별도로 결정한다.
- S3 전환 전까지 DB의 `storage_backend=local`, `storage_key=<local path>` 기준으로 저장한다.

## JSON Assets -> `assets`

| JSON field | DB column | 비고 |
| --- | --- | --- |
| `assetId` | `assets.id` | 기존 asset id 유지 |
| `type` | `assets.asset_type` | 예: `input_image`, `output_image` |
| `fileName` | `assets.file_name` | 다운로드 파일명 |
| `mimeType` | `assets.mime_type` | 없으면 추정값 또는 `application/octet-stream` |
| `sizeBytes` | `assets.size_bytes` | 파일 크기 |
| `path` | `assets.storage_key` | local backend에서는 절대/로컬 경로 |
| - | `assets.storage_backend` | 현재 `local`, 추후 `s3` |
| `downloadUrl`, `kind`, 기타 | `assets.metadata_json` | 필요 시 보존 |
| `createdAt` | `assets.created_at` | 파싱 실패 시 현재 시각 |

API 반환 시에는 기존처럼 `assetId`, `type`, `fileName`, `mimeType`, `sizeBytes`, `path`, `createdAt` 형태를 만든다.

## JSON History -> `workflow_tasks`

| JSON field | DB column | 비고 |
| --- | --- | --- |
| `taskId` | `workflow_tasks.id` | 작업 id |
| `runpodJobId` | `workflow_tasks.runpod_job_id` | RunPod job id |
| `workflowId` | `workflow_tasks.workflow_id` | workflow json 파일명 |
| `executionMode` | `workflow_tasks.execution_mode` | `dry-run` 또는 `runpod` |
| `status` | `workflow_tasks.status` | UI 표시 상태 |
| `user.id` | `workflow_tasks.user_id` / `users.id` | 없으면 null |
| `workerName` | `workflow_tasks.worker_name` | 작업자 표시명 |
| `timestamp` | `workflow_tasks.started_at`, `created_at` | 작업 시작/표시 시간 |
| `positivePrompts` | `workflow_tasks.positive_prompts` | JSON list |
| `negativePrompts` | `workflow_tasks.negative_prompts` | JSON list |
| `configJson` | `workflow_tasks.config_json` | 첫 segment 기준 config |
| `wanNodeConfig` | `workflow_tasks.wan_node_config` | 서브그래프/노드별 설정 snapshot |
| `patchSummary` | `workflow_tasks.patch_summary` | workflow patch 결과 |
| 전체 history item | `workflow_tasks.payload_json` | API 호환 복원을 위한 원본 보존 |
| RunPod submit/status | `runpod_submit_json`, `runpod_status_json` | 추후 실행 복구/진단용 |

## History Asset Links

| JSON field | DB table | 비고 |
| --- | --- | --- |
| `inputAssets[]` | `task_input_assets` | `slot_index`는 배열 순서 |
| `inputImages[].assetId` | `task_input_assets` | `inputAssets` 누락 시 보완 |
| `keyframes[].uploadId` | `task_input_assets` | 재작업 입력 이미지 복원 기준 |
| `outputAssets[]` | `task_output_assets` | `output_role`, `segment_index` 보존 |

## JSON Configs -> `config_snapshots`

| JSON field | DB column | 비고 |
| --- | --- | --- |
| `configId` | `config_snapshots.id` | 저장 config id |
| `workflowId` | `config_snapshots.workflow_id` | workflow json 파일명 |
| `name` | `config_snapshots.name` | UI 표시명 |
| `source` | `config_snapshots.source` | 기본 `studio` |
| `user.id` | `config_snapshots.user_id` | 사용자 FK, 없으면 null |
| 전체 config item 또는 `snapshot` | `snapshot_json` | API 호환 복원 기준 |
| `timestamp` | `created_at` | 파싱 실패 시 현재 시각 |

## 삭제 정책

- `delete_history_item(task_id)`는 task row와 link row를 삭제한다.
- 연결된 asset은 다른 task link에서 참조하지 않을 때 DB row와 local file을 삭제한다.
- config snapshot 내부 JSON에만 남은 asset 참조는 FK가 아니므로 별도 이관/정리 스크립트에서 검토한다.
- S3 adapter 도입 후에는 `storage_backend=s3`인 asset 삭제가 S3 object delete로 이어져야 한다.

## 아직 남은 결정 사항

- `JOBS` 메모리 상태를 DB에 저장할지 여부
- 실행 중 서버 재시작 시 RunPod `/status/{job_id}`로 복구할 job 범위
- JSON 기존 데이터 이관 시 잘못된 과거 절대경로를 어떻게 보정할지
- config snapshot이 참조하는 input asset을 삭제 보호 대상으로 볼지 여부

## 로컬 이관 명령

기본 dry-run:

```bash
python3 scripts/migrate_json_to_db.py
```

로컬 MySQL 적용:

```bash
python3 scripts/migrate_json_to_db.py --apply \
  --database-url mysql+pymysql://dobedub:dobedub_password@127.0.0.1:3306/dobedub_studio
```

2026-08-02 로컬 검증 결과:

- assets 39개 이관
- history 10개 이관
- configs 2개 이관
- `PERSISTENCE_BACKEND=db` API smoke 통과
