from sqlalchemy import create_engine, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.config import settings

_connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=_connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def ensure_schema() -> None:
    """现网升级兼容：为已存在的 Postgres 表幂等补列（新表由 create_all 建立）。"""
    if engine.dialect.name != "postgresql":
        return
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE halls ADD COLUMN IF NOT EXISTS absent_policy VARCHAR(16)"))
        conn.execute(text("ALTER TABLE candidates ADD COLUMN IF NOT EXISTS absent BOOLEAN NOT NULL DEFAULT FALSE"))


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
