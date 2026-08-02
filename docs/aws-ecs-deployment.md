# AWS ECS 배포 가이드

이 문서는 기존 Gradio 기반 `Serverless_ComfyUI` ECS 서비스를 `DOBEDUB STUDIO` 앱으로 교체하기 위한 배포 절차입니다.

## 전제

- AWS 리전: `ap-northeast-2`
- ECS 클러스터: `default`
- ECS 서비스: `dobedub-app`
- 기존 ECS 서비스 컨테이너 포트: `7860`
- RunPod 실행 모드: `RUNPOD_DRY_RUN=0`

## 필수 환경변수

ECS task definition 또는 secret manager에 아래 값을 설정합니다.

```text
HOST=0.0.0.0
PORT=7860
WORKFLOWS_DIR=/app/workflows
STUDIO_DATA_DIR=/data/outputs/dobedub-studio
OUTPUTS_DIR=/data/outputs/dobedub-studio/outputs
RUNPOD_DRY_RUN=0
RUNPOD_API_KEY=<secret>
RUNPOD_ENDPOINT_ID=<endpoint-id>
RUNPOD_BASE_URL=https://api.runpod.ai/v2
```

## 이미지 빌드

```bash
docker build -t dobedub-studio:latest .
```

## ECR 푸시

```bash
AWS_REGION=ap-northeast-2
AWS_ACCOUNT_ID=<account-id>
ECR_REPOSITORY=dobedub_studio

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$AWS_REGION" || true

docker tag dobedub-studio:latest "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
docker push "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:latest"
```

## ECS 업데이트 개요

1. 기존 서비스의 task definition을 조회합니다.
2. container image를 새 ECR 이미지로 교체합니다.
3. 기존 서비스의 target group/port를 유지하려면 container port가 `7860`인지 확인합니다.
4. `RUNPOD_API_KEY`는 plaintext env보다 Secrets Manager 또는 SSM Parameter Store 참조를 권장합니다.
5. 새 task definition revision을 등록합니다.
6. `dobedub-app` 서비스를 새 revision으로 업데이트합니다.
7. 새 task가 healthy 상태가 된 뒤 이전 task가 drain되는지 확인합니다.

## 운영 저장소 주의

현재 앱은 `data/*.json`, `data/uploads`, `data/outputs`를 로컬 파일로 사용합니다. ECS task가 재시작되면 컨테이너 내부 데이터는 사라질 수 있으므로 운영에서는 아래 중 하나를 적용해야 합니다.

- 임시 운영: 기존처럼 stateless로 두고 작업 이력/결과 파일은 재시작 시 초기화 허용
- 권장 운영: EFS를 `/app/data`에 mount
- 장기 운영: 작업 이력은 DB, 결과 asset은 S3로 이전

## 운영 배포 기록

운영 계정 ID, ECR URI, task definition ARN, secret ARN 등은 공개 저장소에 기록하지 않습니다.
배포 이력은 AWS ECS console, CloudTrail, 또는 내부 운영 문서에서 관리합니다.
