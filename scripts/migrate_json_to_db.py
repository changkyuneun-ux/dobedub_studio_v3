#!/usr/bin/env python3
"""Migrate JSON persistence files into the SQLAlchemy database.

Default mode is dry-run. Pass --apply to write to the target database.
Run Alembic first by default so a fresh local DB can be prepared in one step.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.repositories.db_adapter import DbStudioRepository  # noqa: E402


def load_json(path: Path, fallback):
    if not path.exists():
        return fallback
    with path.open("r", encoding="utf-8") as stream:
        return json.load(stream)


def migrate_schema(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    config = Config(str(PROJECT_ROOT / "alembic.ini"))
    command.upgrade(config, "head")


def migrate_json_to_db(*, data_dir: Path, database_url: str, apply: bool, upgrade: bool = True) -> dict:
    data_dir = Path(data_dir)
    assets_path = data_dir / "assets.json"
    history_path = data_dir / "history.json"
    configs_path = data_dir / "configs.json"
    uploads_dir = data_dir / "uploads"
    outputs_dir = data_dir / "outputs"

    assets = load_json(assets_path, {})
    history = load_json(history_path, [])
    configs = load_json(configs_path, [])
    summary = {
        "dataDir": str(data_dir),
        "assets": len(assets),
        "history": len(history),
        "configs": len(configs),
        "applied": bool(apply),
    }
    if not apply:
        return summary

    if upgrade:
        migrate_schema(database_url)

    engine = create_engine(database_url, future=True)
    Session = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
    session = Session()
    try:
        repo = DbStudioRepository(session, uploads_dir=uploads_dir, outputs_dir=outputs_dir)
        for item in assets.values():
            if isinstance(item, dict):
                repo.upsert_asset_record(item)
        for item in configs:
            if isinstance(item, dict):
                repo.append_config(item)
        for item in reversed(history):
            if isinstance(item, dict):
                repo.append_history(item)
        summary["dbHistory"] = len(repo.load_history())
        summary["dbConfigs"] = len(repo.load_configs())
    finally:
        session.close()
        engine.dispose()
    return summary


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Migrate DOBEDUB JSON persistence files to DB.")
    parser.add_argument("--data-dir", default=os.environ.get("STUDIO_DATA_DIR", str(PROJECT_ROOT / "data")))
    parser.add_argument("--database-url", default=os.environ.get("DATABASE_URL", "sqlite:///./data/dobedub-studio.db"))
    parser.add_argument("--apply", action="store_true", help="Write data to the database. Omit for dry-run.")
    parser.add_argument("--skip-upgrade", action="store_true", help="Do not run Alembic upgrade before migration.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    summary = migrate_json_to_db(
        data_dir=Path(args.data_dir),
        database_url=args.database_url,
        apply=args.apply,
        upgrade=not args.skip_upgrade,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
