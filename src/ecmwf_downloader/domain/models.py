"""Stable domain models shared by the CLI, API and worker."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskStatus(str, Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRY_WAIT = "retry_wait"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class SplitStrategy(str, Enum):
    NONE = "none"
    YEAR = "year"
    MONTH = "month"


class AccountStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"


VALID_TRANSITIONS: dict[TaskStatus, set[TaskStatus]] = {
    TaskStatus.PENDING: {TaskStatus.QUEUED, TaskStatus.CANCELLED},
    TaskStatus.QUEUED: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.RUNNING: {
        TaskStatus.COMPLETED,
        TaskStatus.FAILED,
        TaskStatus.RETRY_WAIT,
        TaskStatus.CANCELLING,
    },
    TaskStatus.RETRY_WAIT: {TaskStatus.RUNNING, TaskStatus.CANCELLED},
    TaskStatus.CANCELLING: {TaskStatus.CANCELLED, TaskStatus.FAILED},
    TaskStatus.COMPLETED: set(),
    TaskStatus.FAILED: {TaskStatus.PENDING, TaskStatus.QUEUED},
    TaskStatus.CANCELLED: {TaskStatus.PENDING, TaskStatus.QUEUED},
}


def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())


class TaskData(BaseModel):
    """Public task representation; never contains account credentials."""

    model_config = ConfigDict(extra="forbid")

    id: str
    dataset_id: str
    request_payload: Dict[str, Any]
    filename: str
    output_path: str
    status: TaskStatus
    split_strategy: SplitStrategy = SplitStrategy.NONE
    progress: Optional[float] = Field(default=None, ge=0, le=100)
    downloaded_bytes: int = Field(default=0, ge=0)
    total_bytes: Optional[int] = Field(default=None, ge=0)
    retry_count: int = Field(default=0, ge=0)
    max_retries: int = Field(default=3, ge=0)
    next_retry_at: Optional[datetime] = None
    error_message: Optional[str] = None
    account_id: Optional[str] = None
    cancel_requested: bool = False
    created_at: datetime
    updated_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class AccountData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    email: str
    url: str
    status: AccountStatus
    used_count: int = 0
    fail_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None


class EventData(BaseModel):
    id: int
    event_type: str
    task_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
