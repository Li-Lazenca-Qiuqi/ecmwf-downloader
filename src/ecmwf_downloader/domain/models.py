"""请求、结果与账号的领域模型。"""
from __future__ import annotations
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, HttpUrl

def utc_now() -> datetime:
    return datetime.now(timezone.utc)

class TaskStatus(str, Enum):
    QUEUED = "queued"
    SUBMITTING = "submitting"
    ACCEPTED = "accepted"
    RUNNING = "running"
    REFRESHING = "refreshing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    SUBMISSION_UNKNOWN = "submission_unknown"

class SplitStrategy(str, Enum):
    NONE = "none"
    YEAR = "year"
    MONTH = "month"
    DAY = "day"
    SMART = "smart"

class AccountStatus(str, Enum):
    ACTIVE = "active"
    DISABLED = "disabled"
    ERROR = "error"



ACTIVE_STATUSES = {TaskStatus.SUBMITTING, TaskStatus.ACCEPTED, TaskStatus.RUNNING,
                   TaskStatus.REFRESHING, TaskStatus.CANCELLING}
VALID_TRANSITIONS = {
    TaskStatus.QUEUED: {TaskStatus.SUBMITTING, TaskStatus.CANCELLED},
    TaskStatus.SUBMITTING: {TaskStatus.ACCEPTED, TaskStatus.COMPLETED, TaskStatus.FAILED,
                           TaskStatus.CANCELLING, TaskStatus.SUBMISSION_UNKNOWN},
    TaskStatus.ACCEPTED: {TaskStatus.CANCELLED, TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.EXPIRED, TaskStatus.CANCELLING},
    TaskStatus.RUNNING: {TaskStatus.ACCEPTED, TaskStatus.CANCELLED, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.EXPIRED, TaskStatus.CANCELLING},
    TaskStatus.REFRESHING: {TaskStatus.CANCELLED, TaskStatus.ACCEPTED, TaskStatus.RUNNING, TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.EXPIRED, TaskStatus.CANCELLING},
    TaskStatus.COMPLETED: {TaskStatus.REFRESHING},
    TaskStatus.FAILED: {TaskStatus.QUEUED, TaskStatus.ACCEPTED, TaskStatus.CANCELLING},
    TaskStatus.CANCELLED: {TaskStatus.QUEUED},
    TaskStatus.EXPIRED: {TaskStatus.QUEUED},
    TaskStatus.CANCELLING: {TaskStatus.CANCELLED, TaskStatus.FAILED, TaskStatus.SUBMISSION_UNKNOWN},
    TaskStatus.SUBMISSION_UNKNOWN: {TaskStatus.ACCEPTED, TaskStatus.CANCELLING},
}
def can_transition(current: TaskStatus, target: TaskStatus) -> bool:
    return target in VALID_TRANSITIONS[current]

class ResultAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")
    url: HttpUrl
    filename: Optional[str] = None
    size: Optional[int] = Field(default=None, ge=0)
    content_type: Optional[str] = None
    expires_at: Optional[datetime] = None

class TaskBatch(BaseModel):
    batch_id: str
    name: str
    position: int
    total: int

class TaskData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    dataset_id: str
    request_payload: dict[str, Any]
    title: str
    batch: Optional[TaskBatch] = None
    status: TaskStatus
    split_strategy: SplitStrategy = SplitStrategy.NONE
    remote_request_id: Optional[str] = None
    remote_status: Optional[str] = None
    results: list[ResultAsset] = Field(default_factory=list)
    checked_at: Optional[datetime] = None
    retry_count: int = 0
    max_retries: int = 3
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
    is_busy: bool = False
    used_count: int = 0
    today_used_count: int = 0
    fail_count: int = 0
    last_used: Optional[datetime] = None
    last_error: Optional[str] = None


class EventData(BaseModel):
    id: int
    event_type: str
    task_id: Optional[str] = None
    payload: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
