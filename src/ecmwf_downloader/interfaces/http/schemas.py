"""HTTP DTOs kept separate from domain entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field

from ecmwf_downloader.domain.models import AccountData, SplitStrategy, TaskData, TaskStatus


class PreviewBody(BaseModel):
    dataset_id: str
    request_payload: dict[str, Any]
    output_dir: Optional[Path] = None
    split_strategy: SplitStrategy = SplitStrategy.NONE
    filename: Optional[str] = None


class TaskCreateBody(PreviewBody):
    max_retries: Optional[int] = Field(default=None, ge=0, le=20)
    overwrite: Optional[bool] = None
    enqueue: bool = False


class TaskListQuery(BaseModel):
    status: Optional[TaskStatus] = None
    search: Optional[str] = None
    limit: int = Field(default=50, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class BatchBody(BaseModel):
    task_ids: list[str] = Field(min_length=1)


class AccountCreateBody(BaseModel):
    email: str
    key: str
    url: str = "https://cds.climate.copernicus.eu/api"
    id: Optional[str] = None


class AccountUpdateBody(BaseModel):
    email: Optional[str] = None
    key: Optional[str] = None
    url: Optional[str] = None


class AccountResponse(AccountData):
    pass


class AISuggestionBody(BaseModel):
    field_schema: dict[str, Any]
    user_request: str


class TemplateBody(BaseModel):
    name: str
    payload: dict[str, Any]


class SettingsPatch(BaseModel):
    values: dict[str, Any]
