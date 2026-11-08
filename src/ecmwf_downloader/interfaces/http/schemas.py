"""HTTP DTOs kept separate from domain entities."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator
from ecmwf_downloader.config import service_url

from ecmwf_downloader.domain.models import AccountData, SplitStrategy, TaskData, TaskStatus


class CostingBody(BaseModel):
    request_payload: dict[str, Any]
    split_strategy: SplitStrategy = SplitStrategy.NONE
    split_count: Optional[int] = Field(default=None, strict=True, ge=2)
    schema_revision: Optional[str] = None
    editor_values: Optional[dict[str, Any]] = None


class PreviewBody(CostingBody):
    model_config = ConfigDict(extra="forbid")
    dataset_id: str


class TaskCreateBody(PreviewBody):
    max_retries: Optional[int] = Field(default=None, ge=0, le=20)

class AttachBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    remote_request_id: str = Field(min_length=1, max_length=255, pattern=r"^[A-Za-z0-9_-]+$")

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
    user_request: str = Field(min_length=1, max_length=12000)


class AIConfigBody(BaseModel):
    model_config = ConfigDict(extra='forbid')
    enabled: bool
    base_url: str = Field(min_length=1, max_length=2048)
    model: str = Field(min_length=1, max_length=200)
    api_key: Optional[SecretStr] = None
    json_mode: bool = True

    @field_validator('base_url')
    @classmethod
    def validate_base_url(cls, value: str) -> str:
        return service_url(value)

    @field_validator('model')
    @classmethod
    def model_name(cls, value: str) -> str:
        if not value.strip():
            raise ValueError('模型名称不能为空')
        return value.strip()


class TemplateBody(BaseModel):
    name: str
    payload: dict[str, Any]


class SettingsPatch(BaseModel):
    values: dict[str, Any]
