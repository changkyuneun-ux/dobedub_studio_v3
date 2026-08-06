#!/usr/bin/env python3
"""Run Alembic database migrations as a one-off task.

Use this script for ECS/CI migration jobs so application startup can stay
focused on serving traffic.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config


PROJECT_ROOT = Path(__file__).resolve().parents[1]
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


def main() -> None:
    if os.environ.get("RUN_MIGRATION_SKIP_ENV_LOAD", "0") != "1":
        load_env_file(PROJECT_ROOT / ".env")
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


if __name__ == "__main__":
    main()
