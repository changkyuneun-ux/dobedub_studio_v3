#!/usr/bin/env python3
"""Synchronize admin and prompt-catalog reference data between databases.

This script intentionally excludes generated task/history/asset rows. It is
for production bootstrap or repair when the application schema exists but the
reference data managed in local development has not been copied to the target DB.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Iterable

from sqlalchemy import DateTime as SaDateTime, create_engine, delete, select, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.db.models import (  # noqa: E402
    ModelProfile,
    Permission,
    PromptCategory,
    PromptCategoryGroup,
    PromptCategoryTerm,
    PromptRule,
    PromptScope,
    PromptSubcategory,
    PromptSubcategoryKeyword,
    PromptSystemPrompt,
    PromptTemplate,
    PromptTerm,
    PromptTermRelation,
    PromptTermRendering,
    Role,
    RolePermission,
    UiPermissionResource,
    User,
    UserPermission,
)
from backend.app.db.session import engine_kwargs  # noqa: E402


SYNC_MODELS = [
    User,
    Role,
    Permission,
    RolePermission,
    UserPermission,
    UiPermissionResource,
    PromptCategory,
    PromptScope,
    PromptCategoryGroup,
    PromptSubcategory,
    PromptTerm,
    PromptCategoryTerm,
    PromptSubcategoryKeyword,
    PromptTermRelation,
    PromptRule,
    PromptTemplate,
    PromptSystemPrompt,
    ModelProfile,
    PromptTermRendering,
]


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


def db_url_from_env(name: str, default: str = "") -> str:
    value = os.environ.get(name, "").strip() or default
    if not value:
        raise SystemExit(f"{name} is required.")
    return value


def make_engine(url: str, *, ssl_ca: str = "", ssl_verify_identity: bool = False) -> Engine:
    return create_engine(
        url,
        future=True,
        **engine_kwargs(url, database_ssl_ca=ssl_ca, database_ssl_verify_identity=ssl_verify_identity),
    )


def row_payloads(session: Session, model) -> list[dict]:
    rows = session.execute(select(model)).scalars().all()
    payloads = []
    for row in rows:
        payloads.append({column.name: getattr(row, column.name) for column in model.__table__.columns})
    return payloads


def serialize_value(value):
    if hasattr(value, "isoformat"):
        return {"__type": "datetime", "value": value.isoformat()}
    return value


def deserialize_value(value):
    if isinstance(value, dict) and value.get("__type") == "datetime":
        raw_value = value.get("value")
        return None if raw_value is None else __import__("datetime").datetime.fromisoformat(raw_value)
    return value


def export_reference_json(source_engine: Engine, path: Path) -> dict:
    with Session(source_engine) as source:
        data = {
            "version": 1,
            "tables": {
                model.__tablename__: [
                    {key: serialize_value(value) for key, value in row.items()}
                    for row in row_payloads(source, model)
                ]
                for model in SYNC_MODELS
            },
        }
        counts = {table: len(rows) for table, rows in data["tables"].items()}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return counts


def load_reference_json(path: Path) -> dict[str, list[dict]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("version") != 1 or not isinstance(data.get("tables"), dict):
        raise SystemExit(f"Unsupported reference data file: {path}")
    tables = {}
    for model in SYNC_MODELS:
        rows = data["tables"].get(model.__tablename__, [])
        normalized_rows = []
        datetime_columns = {
            column.name
            for column in model.__table__.columns
            if isinstance(column.type, SaDateTime)
        }
        for row in rows:
            normalized_rows.append({
                key: deserialize_value(value) if key in datetime_columns else value
                for key, value in row.items()
            })
        tables[model.__tablename__] = normalized_rows
    return tables


def count_rows(session: Session, models: Iterable) -> dict[str, int]:
    counts: dict[str, int] = {}
    for model in models:
        counts[model.__tablename__] = len(session.execute(select(model)).scalars().all())
    return counts


def disable_fk_checks(session: Session) -> None:
    if session.bind and session.bind.dialect.name == "mysql":
        session.execute(text("SET FOREIGN_KEY_CHECKS=0"))


def enable_fk_checks(session: Session) -> None:
    if session.bind and session.bind.dialect.name == "mysql":
        session.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def sync_reference_data(source_engine: Engine | None, target_engine: Engine, *, dry_run: bool = False, source_tables: dict[str, list[dict]] | None = None) -> dict:
    with Session(target_engine) as target:
        if source_tables is None:
            if source_engine is None:
                raise SystemExit("source_engine or source_tables is required.")
            with Session(source_engine) as source:
                source_counts = count_rows(source, SYNC_MODELS)
                source_tables = {model.__tablename__: row_payloads(source, model) for model in SYNC_MODELS}
        else:
            source_counts = {model.__tablename__: len(source_tables.get(model.__tablename__, [])) for model in SYNC_MODELS}
        if dry_run:
            return {"dryRun": True, "sourceCounts": source_counts, "targetCounts": count_rows(target, SYNC_MODELS)}

        disable_fk_checks(target)
        try:
            for model in reversed(SYNC_MODELS):
                target.execute(delete(model))
            target.flush()

            inserted: dict[str, int] = {}
            for model in SYNC_MODELS:
                payloads = source_tables.get(model.__tablename__, [])
                if payloads:
                    target.execute(model.__table__.insert(), payloads)
                inserted[model.__tablename__] = len(payloads)
            target.commit()
        except Exception:
            target.rollback()
            raise
        finally:
            enable_fk_checks(target)
            target.commit()

        with Session(target_engine) as verify:
            return {"dryRun": False, "sourceCounts": source_counts, "targetCounts": count_rows(verify, SYNC_MODELS), "inserted": inserted}


def print_counts(title: str, counts: dict[str, int]) -> None:
    print(title)
    for table, count in counts.items():
        print(f"  {table}: {count}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sync local reference data to a target DB.")
    parser.add_argument("--source-url", default="", help="Source SQLAlchemy URL. Defaults to SOURCE_DATABASE_URL or local SQLite.")
    parser.add_argument("--target-url", default="", help="Target SQLAlchemy URL. Defaults to TARGET_DATABASE_URL or DATABASE_URL.")
    parser.add_argument("--target-ssl-ca", default="", help="Target MySQL/RDS CA bundle path.")
    parser.add_argument("--target-ssl-verify-identity", action="store_true", help="Enable MySQL ssl_verify_identity.")
    parser.add_argument("--export-json", default="", help="Export source reference data to this JSON file and exit.")
    parser.add_argument("--source-json", default="", help="Import reference data from this JSON file instead of a source DB.")
    parser.add_argument("--dry-run", action="store_true", help="Print counts without modifying the target.")
    args = parser.parse_args()

    load_env_file(PROJECT_ROOT / ".env")
    source_url = args.source_url or db_url_from_env("SOURCE_DATABASE_URL", "sqlite:///./data/dobedub-studio.db")
    if args.export_json:
        source_engine = make_engine(source_url)
        counts = export_reference_json(source_engine, Path(args.export_json))
        print_counts("exported", counts)
        return

    target_url = args.target_url or os.environ.get("TARGET_DATABASE_URL") or db_url_from_env("DATABASE_URL")
    target_ssl_ca = args.target_ssl_ca or os.environ.get("TARGET_DATABASE_SSL_CA") or os.environ.get("DATABASE_SSL_CA", "")
    target_ssl_verify_identity = args.target_ssl_verify_identity or os.environ.get("TARGET_DATABASE_SSL_VERIFY_IDENTITY", "0") in {"1", "true", "TRUE", "yes", "YES"}

    source_tables = load_reference_json(Path(args.source_json)) if args.source_json else None
    source_engine = None if source_tables is not None else make_engine(source_url)
    target_engine = make_engine(target_url, ssl_ca=target_ssl_ca, ssl_verify_identity=target_ssl_verify_identity)
    result = sync_reference_data(source_engine, target_engine, dry_run=args.dry_run, source_tables=source_tables)
    print_counts("sourceCounts", result["sourceCounts"])
    print_counts("targetCounts", result["targetCounts"])
    if not result["dryRun"]:
        print_counts("inserted", result["inserted"])


if __name__ == "__main__":
    main()
