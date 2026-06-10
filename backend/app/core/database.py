from collections.abc import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _make_engine():
    settings = get_settings()
    url = settings.database_url
    connect_args = {}
    if url.startswith("sqlite"):
        # SQLite (tests) needs this flag; MySQL ignores it.
        connect_args["check_same_thread"] = False
    elif settings.db_ssl:
        # Hosted MySQL (e.g. Aiven) requires TLS. This encrypts the connection in
        # transit; the managed provider's certificate isn't strictly verified, which
        # is an acceptable trade-off for this deployment.
        import ssl as _ssl
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        connect_args["ssl"] = ctx
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


engine = _make_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
