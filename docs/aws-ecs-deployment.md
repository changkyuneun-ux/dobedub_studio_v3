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
PERSISTENCE_BACKEND=db
DATABASE_URL=mysql+pymysql://<user>:<password>@<rds-endpoint>:3306/dobedub_studio
DATABASE_ECHO=0
DATABASE_SSL_CA=/app/certs/global-bundle.pem
DATABASE_SSL_VERIFY_IDENTITY=1
STORAGE_BACKEND=s3
S3_BUCKET=<asset-bucket>
S3_PREFIX=dobedub-studio
RUNPOD_DRY_RUN=0
RUNPOD_API_KEY=<secret>
RUNPOD_ENDPOINT_ID=<endpoint-id>
RUNPOD_BASE_URL=https://api.runpod.ai/v2
PROMPT_LLM_PROVIDER=runpod_vllm
PROMPT_LLM_API_KEY=<secret>
PROMPT_LLM_ENDPOINT_ID=<qwen-endpoint-id>
PROMPT_LLM_RUNPOD_INPUT_MODE=prompt
PROMPT_LLM_TIMEOUT=240
AUTH_JWT_SECRET=<strong-random-secret>
AUTH_TOKEN_TTL_MINUTES=480
RUN_SERVER_AUTO_MIGRATE=0
```

`RUNPOD_API_KEY`, `PROMPT_LLM_API_KEY`, `DATABASE_URL`, `AUTH_JWT_SECRET`는 Secrets Manager 또는 SSM Parameter Store 참조로 주입합니다. `PROMPT_LLM_API_KEY`가 같은 RunPod key를 쓰는 경우에도 별도 secret으로 분리해 두면 endpoint 교체가 쉽습니다. `DATABASE_SSL_CA`는 AWS RDS 콘솔이 안내하는 `global-bundle.pem` 경로를 container 안의 실제 파일 위치로 지정합니다. `DATABASE_SSL_VERIFY_IDENTITY=1`은 RDS 권장 접속 방식과 맞춥니다. `RUN_SERVER_AUTO_MIGRATE=0`으로 두고, migration은 one-off task로 분리합니다.

인증은 `Authorization: Bearer <JWT>`만 허용합니다. `AUTH_TRUST_PROXY_HEADERS` 및 `X-User-*` 헤더 기반 인증은 지원하지 않으므로, ECS task definition에서도 해당 환경변수를 제거합니다.

## RDS/MySQL 운영 기준

- ECS task 내부에 MySQL을 실행하지 않습니다. 운영 DB는 Amazon RDS MySQL 또는 Aurora MySQL을 사용합니다.
- `DATABASE_URL`은 ECS task definition의 plaintext 환경변수보다 Secrets Manager 또는 SSM Parameter Store 참조를 권장합니다.
- `DATABASE_SSL_CA`와 `DATABASE_SSL_VERIFY_IDENTITY`를 설정해 RDS CA 검증을 함께 활성화합니다.
- RDS security group은 ECS task security group에서 오는 3306 inbound만 허용합니다.
- 기본 운영에서는 `PERSISTENCE_BACKEND=db`인 경우 웹 task 시작 시 migration을 하지 않고, 별도 one-off ECS task 또는 CI/CD 단계에서 `alembic upgrade head`를 먼저 실행합니다.
- 웹 task는 `RUN_SERVER_AUTO_MIGRATE=0`을 유지해 app startup과 DB schema 변경을 분리합니다.
- 애플리케이션 task는 migration 완료 후 새 revision으로 교체합니다.
- Docker image의 기본 entrypoint는 `scripts/run_server.py`입니다. 앱 시작 시에는 serving만 담당하고, DB migration은 `scripts/upgrade_database.py`를 one-off task로 실행합니다.

로컬 migration 검증:

```bash
python3 scripts/db_migration_smoke_check.py
```

운영 migration 예시:

```bash
DATABASE_URL='mysql+pymysql://<user>:<password>@<rds-endpoint>:3306/dobedub_studio' \
DATABASE_SSL_CA='/app/certs/global-bundle.pem' \
DATABASE_SSL_VERIFY_IDENTITY=1 \
  python3 scripts/upgrade_database.py
```

## Asset 저장소 기준

DB에는 파일 바이너리를 저장하지 않습니다. DB에는 `asset_id`, `file_name`, `mime_type`, `size_bytes`, `storage_backend`, `storage_key`, `public_url` 등 메타데이터만 저장합니다.

- 현재 호환 경로: JSON metadata + local/EFS 파일
- ECS 과도기 권장: EFS mount + RDS
- 장기 권장: S3 asset storage + RDS metadata

## 이미지 빌드

```bash
IMAGE_TAG=$(git rev-parse --short HEAD)
docker buildx build --platform linux/amd64 --load -t dobedub-studio:${IMAGE_TAG} .
```

Apple Silicon Mac에서 기본 `docker build`를 사용하면 ARM64 이미지가 만들어질 수 있습니다. 현재 ECS Fargate 서비스는 `linux/amd64`이므로, ECR에 직접 올릴 때도 반드시 `--platform linux/amd64`를 지정합니다.

`.dockerignore`는 로컬 SQLite DB, 업로드 이미지, 생성 영상, 리포트, `.env`를 이미지에 포함하지 않도록 구성되어야 합니다. 운영에 필요한 기본 파일은 `data/segment-defaults.json`만 포함합니다.

## ECR 푸시

```bash
AWS_REGION=ap-northeast-2
AWS_ACCOUNT_ID=<account-id>
ECR_REPOSITORY=dobedub_studio

aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com"

aws ecr create-repository --repository-name "$ECR_REPOSITORY" --region "$AWS_REGION" || true

IMAGE_TAG=$(git rev-parse --short HEAD)
docker buildx build --platform linux/amd64 --push \
  -t "$AWS_ACCOUNT_ID.dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPOSITORY:${IMAGE_TAG}" .
```

## ECS 업데이트 개요

1. 기존 서비스의 task definition을 조회합니다.
2. container image를 새 ECR 이미지로 교체합니다. `latest` 대신 immutable tag(git SHA/build number)를 사용합니다.
3. 기존 서비스의 target group/port를 유지하려면 container port가 `7860`인지 확인합니다.
4. `RUNPOD_API_KEY`는 plaintext env보다 Secrets Manager 또는 SSM Parameter Store 참조를 권장합니다.
5. 새 task definition revision을 등록합니다.
6. `dobedub-app` 서비스를 새 revision으로 업데이트합니다.
7. 새 task가 healthy 상태가 된 뒤 이전 task가 drain되는지 확인합니다.
8. 별도 migration 작업이 필요한 경우 `scripts/upgrade_database.py`를 one-off task로 먼저 실행합니다.

## 운영 저장소 주의

현재 production-compatible 경로는 `data/*.json`, `data/uploads`, `data/outputs`를 로컬 파일로 사용합니다. ECS task가 재시작되면 컨테이너 내부 데이터는 사라질 수 있으므로 운영에서는 아래 중 하나를 적용해야 합니다.

- 임시 운영: 기존처럼 stateless로 두고 작업 이력/결과 파일은 재시작 시 초기화 허용
- 권장 운영: EFS를 `/app/data`에 mount
- 장기 운영: 작업 이력은 RDS, 결과 asset은 S3로 이전

## 운영 배포 기록

운영 계정 ID, ECR URI, task definition ARN, secret ARN 등은 공개 저장소에 기록하지 않습니다.
배포 이력은 AWS ECS console, CloudTrail, 또는 내부 운영 문서에서 관리합니다.
