#!/usr/bin/env python3
"""Check or run Alembic database migrations as a one-off task.

Use this script for ECS/CI migration jobs so application startup can stay
focused on serving traffic.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from alembic.script import ScriptDirectory


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


def migration_state(config: Config) -> dict[str, object]:
    """Compare the connected database revision to this image's Alembic head."""
    from backend.app.db.session import create_db_engine

    script_directory = ScriptDirectory.from_config(config)
    target_heads = sorted(script_directory.get_heads())
    engine = create_db_engine()
    try:
        with engine.connect() as connection:
            current_heads = sorted(MigrationContext.configure(connection).get_current_heads())
    finally:
        engine.dispose()
    return {
        "currentHeads": current_heads,
        "targetHeads": target_heads,
        "migrationRequired": current_heads != target_heads,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check or apply DOBEDUB STUDIO Alembic migrations.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="Print revision state and exit 2 when migration is required.")
    mode.add_argument("--if-needed", action="store_true", help="Apply migrations only when the database is behind this image.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if os.environ.get("RUN_MIGRATION_SKIP_ENV_LOAD", "0") != "1":
        load_env_file(PROJECT_ROOT / ".env")
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    state = migration_state(config)
    print(json.dumps(state, ensure_ascii=False, sort_keys=True))

    if args.check:
        # Non-zero makes the pending state easy to branch on in CI/CD while
        # keeping connection failures distinct from an up-to-date database.
        return 2 if state["migrationRequired"] else 0
    if args.if_needed and not state["migrationRequired"]:
        print("Database schema is already at the Alembic head; migration skipped.")
        return 0

    command.upgrade(config, "head")
    print("Database migration completed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
