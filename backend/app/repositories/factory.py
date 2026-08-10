from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from backend.app.core.config import get_settings
from backend.app.repositories.db_adapter import DbStudioRepository
from backend.app.repositories.interfaces import StudioRepository
from backend.app.repositories.json_adapter import JsonStudioRepository


def data_paths() -> dict[str, Path]:
    settings = get_settings()
    data_dir = settings.data_dir
    return {
        "history": data_dir / "history.json",
        "assets": data_dir / "assets.json",
        "configs": data_dir / "configs.json",
        "uploads": data_dir / "uploads",
        "outputs": data_dir / "outputs",
        "reports": data_dir / "reports",
    }


def json_repository() -> JsonStudioRepository:
    paths = data_paths()
    return JsonStudioRepository(
        history_path=paths["history"],
        assets_path=paths["assets"],
        configs_path=paths["configs"],
        uploads_dir=paths["uploads"],
        outputs_dir=paths["outputs"],
    )


@contextmanager
def studio_repository() -> Iterator[StudioRepository]:
    settings = get_settings()
    if settings.persistence_backend == "db":
        from backend.app.db.session import SessionLocal

        session = SessionLocal()
        paths = data_paths()
        try:
            yield DbStudioRepository(session, uploads_dir=paths["uploads"], outputs_dir=paths["outputs"])
        finally:
            session.close()
        return
    if settings.persistence_backend != "json":
        raise ValueError(f"Unsupported PERSISTENCE_BACKEND: {settings.persistence_backend}")
    yield json_repository()


@contextmanager
def history_repository() -> Iterator[DbStudioRepository]:
    """Task history storage is DB-only, independent of PERSISTENCE_BACKEND (D-03).

    PERSISTENCE_BACKEND still selects the backend used for assets/configs/
    uploads via studio_repository(), but history read/append/delete always
    goes through the DB adapter so a json-mode deployment can never serve or
    persist task history from/to the legacy JSON files.
    """
    from backend.app.db.session import SessionLocal

    session = SessionLocal()
    paths = data_paths()
    try:
        yield DbStudioRepository(session, uploads_dir=paths["uploads"], outputs_dir=paths["outputs"])
    finally:
        session.close()
