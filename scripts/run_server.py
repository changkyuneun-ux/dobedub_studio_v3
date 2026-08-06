#!/usr/bin/env python3
"""Run DOBEDUB STUDIO in a production container.

This entrypoint is optimized for production container launch. It serves the
app only; run database migrations separately with `scripts/upgrade_database.py`
or set `RUN_SERVER_AUTO_MIGRATE=1` explicitly when you really want startup
migration.
Catalog seed data is intentionally not created automatically in production mode.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Final

import uvicorn
from alembic import command
from alembic.config import Config


PROJECT_ROOT: Final = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and os.environ.get(key) is None:
            os.environ[key] = value


def prepare_database() -> None:
    if os.environ.get("RUN_SERVER_AUTO_MIGRATE", "0") != "1":
        return
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


def prepare_runtime() -> None:
    if os.environ.get("RUN_SERVER_SKIP_ENV_LOAD", "0") != "1":
        load_env_file(PROJECT_ROOT / ".env")
    prepare_database()


def main() -> None:
    prepare_runtime()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8787"))
    uvicorn.run("backend.app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    main()
