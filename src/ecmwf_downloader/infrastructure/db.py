"""SQLite persistence with process-safe settings for the worker and API."""

from __future__ import annotations

import json
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Iterator, Optional

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    Integer,
    String,
    Text,
    create_engine,
    event,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column


def json_dumps(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"), default=str)


def json_loads(value: Optional[str]) -> dict[str, Any]:
    if not value:
        return {}
    try:
        loaded = json.loads(value)
        return loaded if isinstance(loaded, dict) else {}
    except (TypeError, ValueError):
        return {}


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    dataset_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    request_payload: Mapped[str] = mapped_column(Text, nullable=False)
    filename: Mapped[str] = mapped_column(String(512), nullable=False)
    output_path: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    split_strategy: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    progress: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    downloaded_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    next_retry_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[Optional[str]] = mapped_column(Text)
    account_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    cancel_requested: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    worker_id: Mapped[Optional[str]] = mapped_column(String(128), index=True)
    lease_expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    overwrite: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    started_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

class TaskEventRow(Base):
    __tablename__ = "task_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    # Events intentionally outlive deleted tasks so that the SSE stream can
    # still report a deletion.  The task id is therefore an indexed reference,
    # not a foreign key.
    task_id: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)



class SchedulerLeaseRow(Base):
    __tablename__ = "scheduler_leases"

    name: Mapped[str] = mapped_column(String(64), primary_key=True)
    owner_id: Mapped[str] = mapped_column(String(128), nullable=False)
    heartbeat_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AccountStateRow(Base):
    __tablename__ = "account_state"

    account_id: Mapped[str] = mapped_column(String(128), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    fail_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_used: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[Optional[str]] = mapped_column(Text)


class RequestTemplateRow(Base):
    __tablename__ = "request_templates"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    payload: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Database:
    """Own one SQLAlchemy engine and provide short-lived sessions."""

    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.engine = create_engine(
            f"sqlite:///{self.path}",
            connect_args={"check_same_thread": False, "timeout": 30},
            future=True,
        )
        self._configure_sqlite()

    def _configure_sqlite(self) -> None:
        @event.listens_for(self.engine, "connect")
        def _set_pragmas(dbapi_connection, _connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.execute("PRAGMA busy_timeout=30000")
            cursor.close()

    def create_schema(self) -> None:
        Base.metadata.create_all(self.engine)

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = Session(self.engine, expire_on_commit=False)
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
