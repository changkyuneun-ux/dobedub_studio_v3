from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class Settings:
    app_name: str = "DOBEDUB STUDIO API"
    api_prefix: str = "/api/v1"
    project_root: Path = PROJECT_ROOT
    workflows_dir: Path = PROJECT_ROOT / "workflows"
    data_dir: Path = PROJECT_ROOT / "data"
    metadata_dir: Path = PROJECT_ROOT / "metadata"
    persistence_backend: str = "json"
    database_url: str = "sqlite:///./data/dobedub-studio.db"
    database_echo: bool = False
    database_ssl_ca: str = ""
    database_ssl_verify_identity: bool = False
    storage_backend: str = "local"
    s3_bucket: str = ""
    s3_prefix: str = "dobedub-studio"
    dry_run: bool = True
    runpod_api_key: str = ""
    runpod_endpoint_id: str = ""
    runpod_base_url: str = "https://api.runpod.ai/v2"
    runpod_timeout: int = 30
    prompt_llm_provider: str = "mock"
    prompt_llm_api_key: str = ""
    prompt_llm_endpoint_id: str = ""
    prompt_llm_endpoint_url: str = ""
    prompt_llm_model: str = ""
    prompt_llm_runpod_input_mode: str = "prompt"
    prompt_llm_temperature: float = 0.2
    prompt_llm_max_tokens: int = 900
    prompt_llm_timeout: int = 45
    auth_jwt_secret: str = "dobedub-studio-local-dev-secret"
    auth_token_ttl_minutes: int = 480


def get_settings() -> Settings:
    dry_run = os.environ.get("RUNPOD_DRY_RUN", "1") != "0"
    try:
        runpod_timeout = int(os.environ.get("RUNPOD_TIMEOUT", "30"))
    except ValueError:
        runpod_timeout = 30
    try:
        prompt_llm_timeout = int(os.environ.get("PROMPT_LLM_TIMEOUT", "45"))
    except ValueError:
        prompt_llm_timeout = 45
    try:
        prompt_llm_temperature = float(os.environ.get("PROMPT_LLM_TEMPERATURE", "0.2"))
    except ValueError:
        prompt_llm_temperature = 0.2
    try:
        prompt_llm_max_tokens = int(os.environ.get("PROMPT_LLM_MAX_TOKENS", "900"))
    except ValueError:
        prompt_llm_max_tokens = 900
    try:
        auth_token_ttl_minutes = int(os.environ.get("AUTH_TOKEN_TTL_MINUTES", "480"))
    except ValueError:
        auth_token_ttl_minutes = 480
    return Settings(
        workflows_dir=Path(os.environ.get("WORKFLOWS_DIR", PROJECT_ROOT / "workflows")),
        data_dir=Path(os.environ.get("STUDIO_DATA_DIR", PROJECT_ROOT / "data")),
        metadata_dir=Path(os.environ.get("METADATA_DIR", PROJECT_ROOT / "metadata")),
        persistence_backend=os.environ.get("PERSISTENCE_BACKEND", "json").strip().lower() or "json",
        database_url=os.environ.get("DATABASE_URL", "sqlite:///./data/dobedub-studio.db"),
        database_echo=os.environ.get("DATABASE_ECHO", "0") in {"1", "true", "TRUE", "yes", "YES"},
        database_ssl_ca=os.environ.get("DATABASE_SSL_CA", ""),
        database_ssl_verify_identity=os.environ.get("DATABASE_SSL_VERIFY_IDENTITY", "0") in {"1", "true", "TRUE", "yes", "YES"},
        storage_backend=os.environ.get("STORAGE_BACKEND", "local"),
        s3_bucket=os.environ.get("S3_BUCKET", ""),
        s3_prefix=os.environ.get("S3_PREFIX", "dobedub-studio"),
        dry_run=dry_run,
        runpod_api_key=os.environ.get("RUNPOD_API_KEY", ""),
        runpod_endpoint_id=os.environ.get("RUNPOD_ENDPOINT_ID", ""),
        runpod_base_url=os.environ.get("RUNPOD_BASE_URL", "https://api.runpod.ai/v2"),
        runpod_timeout=runpod_timeout,
        prompt_llm_provider=os.environ.get("PROMPT_LLM_PROVIDER", "mock").strip().lower() or "mock",
        prompt_llm_api_key=os.environ.get("PROMPT_LLM_API_KEY", ""),
        prompt_llm_endpoint_id=os.environ.get("PROMPT_LLM_ENDPOINT_ID", ""),
        prompt_llm_endpoint_url=os.environ.get("PROMPT_LLM_ENDPOINT_URL", ""),
        prompt_llm_model=os.environ.get("PROMPT_LLM_MODEL", ""),
        prompt_llm_runpod_input_mode=os.environ.get("PROMPT_LLM_RUNPOD_INPUT_MODE", "prompt").strip().lower() or "prompt",
        prompt_llm_temperature=prompt_llm_temperature,
        prompt_llm_max_tokens=prompt_llm_max_tokens,
        prompt_llm_timeout=prompt_llm_timeout,
        auth_jwt_secret=os.environ.get("AUTH_JWT_SECRET", "dobedub-studio-local-dev-secret"),
        auth_token_ttl_minutes=auth_token_ttl_minutes,
    )
