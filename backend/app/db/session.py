from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from backend.app.core.config import get_settings


def engine_kwargs(database_url: str, *, database_ssl_ca: str = "", database_ssl_verify_identity: bool = False) -> dict:
    if database_url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}

    connect_args: dict[str, object] = {}
    url = make_url(database_url)
    drivername = url.drivername.lower()
    if drivername.startswith("mysql") and database_ssl_ca:
        connect_args["ssl_ca"] = database_ssl_ca
        connect_args["ssl_verify_cert"] = True
        connect_args["ssl_verify_identity"] = database_ssl_verify_identity

    return {
        "pool_pre_ping": True,
        "pool_recycle": 280,
        "connect_args": connect_args,
    }


def create_db_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        echo=settings.database_echo,
        future=True,
        **engine_kwargs(
            settings.database_url,
            database_ssl_ca=settings.database_ssl_ca,
            database_ssl_verify_identity=settings.database_ssl_verify_identity,
        ),
    )


engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
