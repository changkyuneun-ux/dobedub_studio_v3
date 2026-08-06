#!/usr/bin/env python3
"""Run Alembic migrations against a local MySQL database and verify tables.

Expected default local URL:
mysql+pymysql://dobedub:dobedub_password@127.0.0.1:3306/dobedub_studio
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import OperationalError


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

DEFAULT_DATABASE_URL = "mysql+pymysql://dobedub:dobedub_password@127.0.0.1:3306/dobedub_studio"

EXPECTED_TABLES = {
    "users",
    "assets",
    "workflow_tasks",
    "task_input_assets",
    "task_output_assets",
    "config_snapshots",
    "prompt_entries",
    "prompt_categories",
    "prompt_category_terms",
    "prompt_terms",
    "prompt_term_relations",
    "prompt_term_renderings",
    "prompt_rules",
    "prompt_templates",
    "prompt_generation_requests",
    "prompt_generation_outputs",
    "prompt_feedback",
    "model_profiles",
    "reports",
}


def database_url() -> str:
    return os.environ.get("DATABASE_URL") or DEFAULT_DATABASE_URL


def wait_for_database(url: str, timeout_seconds: int = 60) -> None:
    deadline = time.time() + timeout_seconds
    last_error = None
    while time.time() < deadline:
        engine = create_engine(url, future=True, pool_pre_ping=True)
        try:
            with engine.connect() as connection:
                connection.execute(text("select 1"))
                return
        except OperationalError as exc:
            last_error = exc
            time.sleep(2)
        finally:
            engine.dispose()
    raise RuntimeError(f"MySQL did not become ready: {last_error}")


def main() -> None:
    url = database_url()
    os.environ["DATABASE_URL"] = url
    wait_for_database(url)

    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")

    engine = create_engine(url, future=True, pool_pre_ping=True)
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_TABLES - tables
    assert not missing, f"Missing tables: {sorted(missing)}"
    with engine.begin() as connection:
        connection.execute(text(
            "insert into users (id, name, role, created_at, updated_at) "
            "values ('user_mysql_smoke', 'MySQL Smoke User', 'operator', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "on duplicate key update name = values(name), updated_at = CURRENT_TIMESTAMP"
        ))
        count = connection.execute(text("select count(*) from users where id = 'user_mysql_smoke'")).scalar_one()
        assert count == 1
    engine.dispose()

    print("OK mysql migration smoke check passed")


if __name__ == "__main__":
    main()
