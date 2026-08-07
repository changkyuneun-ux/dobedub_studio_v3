# RunPod ComfyUI 모델 정리 가이드

## 목적

등록된 DOBEDUB workflow가 직접 참조하는 모델 파일을 추출하고, RunPod ComfyUI 모델 디렉터리와 대조해 삭제 검토 후보를 확인합니다. 이 도구는 파일을 삭제하거나 이동하지 않습니다.

## 실행 위치

실제 모델 파일 존재 여부와 용량까지 확인하려면 ComfyUI 모델 볼륨을 마운트한 RunPod Pod 또는 해당 볼륨에 접근 가능한 환경에서 실행해야 합니다. ECS 앱 컨테이너는 RunPod 모델 디스크에 접근하지 않으므로, ECS에서 실행하면 workflow 참조 목록만 생성됩니다.

Mac 로컬에서 실행할 때는 `/app`, `/workspace` 같은 RunPod 컨테이너 경로를 사용하면 안 됩니다. 로컬에서는 아래 명령으로 workflow 참조 목록만 먼저 생성할 수 있습니다.

```bash
python3 scripts/export_workflow_model_inventory.py \
  --workflows-dir workflows \
  --output-dir "$HOME/Desktop/model-inventory"
```

## 실행 명령

`runpod-slim` ComfyUI 컨테이너에는 DOBEDUB 프로젝트의 `scripts/` 폴더가 기본 포함되어 있지 않습니다. 따라서 [runpod_workflow_model_inventory.py](../scripts/runpod_workflow_model_inventory.py)와 workflow JSON 디렉터리를 Pod에 먼저 업로드해야 합니다. 이 파일은 Python 표준 라이브러리만 사용하므로 별도 설치가 필요 없습니다.

RunPod JupyterLab 파일 탐색기에서 다음 두 항목을 `/workspace/runpod-slim/inventory-input`에 업로드합니다.

1. `scripts/runpod_workflow_model_inventory.py`
2. DOBEDUB의 `workflows` 폴더 전체

Pod 터미널에서 모델 및 workflow 경로를 먼저 찾습니다.

```bash
find /workspace -type d -name models 2>/dev/null
find /workspace -type d -name workflows 2>/dev/null
```

그 다음, 실제 경로로 바꿔 실행합니다. 결과는 Pod 재시작 전에 다운로드할 수 있도록 `/workspace/runpod-slim/model-inventory`에 저장합니다.

```bash
python3 /workspace/runpod-slim/inventory-input/runpod_workflow_model_inventory.py \
  --workflows-dir /workspace/runpod-slim/inventory-input/workflows \
  --models-dir /workspace/ComfyUI/models \
  --output-dir /workspace/runpod-slim/model-inventory
```

모델 경로를 모를 때는 먼저 확인합니다.

```bash
find /workspace -type d -path '*/ComfyUI/models' 2>/dev/null
```

## 결과 파일

- `workflow-model-inventory.json`: workflow, 노드, 입력 필드까지 포함한 상세 결과
- `workflow-model-inventory.csv`: 스프레드시트 검토용 요약

주요 상태는 다음과 같습니다.

| 상태 | 의미 | 조치 |
| --- | --- | --- |
| `present` | workflow가 참조하며 실제 디스크에도 존재 | 유지 |
| `missing` | workflow가 참조하지만 디스크에 없음 | 삭제가 아니라 workflow/모델 배포 상태 확인 |
| `unused-candidate` | 현재 등록 workflow에서 직접 참조되지 않음 | 즉시 삭제하지 말고 격리 후 테스트 |
| `not-scanned` | `--models-dir` 없이 실행 | 실제 파일 여부 판단 불가 |

## 안전한 정리 순서

1. JSON과 CSV의 `missing` 항목이 없는지 먼저 확인합니다.
2. `unused-candidate`를 별도 `quarantine` 디렉터리로 이동합니다.
3. DOBEDUB에서 활성 workflow를 각각 한 번 이상 생성 테스트합니다.
4. 문제 없음을 확인한 뒤에만 격리 파일을 삭제합니다.

이 리포트는 workflow JSON의 직접 선택값을 기준으로 합니다. custom node가 코드 내부에서 임의 파일을 로드하는 경우는 포착하지 못할 수 있으므로, custom node 관련 파일과 Python 패키지는 이 목록만으로 삭제하지 않아야 합니다.
