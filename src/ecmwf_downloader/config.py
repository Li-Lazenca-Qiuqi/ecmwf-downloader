"""Application and filesystem configuration."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Annotated, Any, Dict, Optional

import yaml
from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator


class RequestSettings(BaseModel):
    model_config = ConfigDict(extra="forbid")
    max_workers: int = Field(default=4, ge=1, le=32, strict=True)
    max_retries: int = Field(default=3, ge=0, le=20, strict=True)
    retry_delays: list[Annotated[FiniteFloat, Field(ge=0, strict=True)]] = Field(default_factory=lambda: [5.0, 15.0, 60.0], min_length=1)
    poll_interval: float = Field(default=5, ge=1, le=3600, strict=True, allow_inf_nan=False)


class AppSettings(BaseModel):
    """Non-secret settings persisted in ``config/app.yaml``."""

    database_path: Path = Path("data/ecmwf.sqlite3")
    config_dir: Path = Path("config")
    requests: RequestSettings = Field(default_factory=RequestSettings)
    ai: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("database_path", "config_dir", mode="before")
    @classmethod
    def expand_paths(cls, value: Any) -> Path:
        return Path(os.path.expandvars(os.path.expanduser(str(value))))

    def resolve_relative_paths(self, base_dir: Optional[Path] = None) -> "AppSettings":
        base = (base_dir or Path.cwd()).resolve()
        values = self.model_dump()
        for key in ("database_path", "config_dir"):
            path = Path(values[key])
            values[key] = path if path.is_absolute() else base / path
        return AppSettings.model_validate(values)


DEFAULT_APP_CONFIG: dict[str, Any] = {
    "database_path": "data/ecmwf.sqlite3",
    "config_dir": "config",
    "requests": {
        "max_workers": 4,
        "max_retries": 3,
        "retry_delays": [5, 15, 60],
        "poll_interval": 5,
    },
    "ai": {
        "enabled": False,
        "base_url": "https://api.openai.com/v1",
        "model": "gpt-4o-mini",
        "temperature": 0.3,
        "timeout": 120,
    },
}


def load_settings(
    config_dir: Path = Path("config"),
    config_path: Optional[Path] = None,
) -> AppSettings:
    """Load settings, creating a minimal example when absent."""

    path = config_path or config_dir / "app.yaml"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            yaml.safe_dump(DEFAULT_APP_CONFIG, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
    with path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return AppSettings.model_validate(data).resolve_relative_paths(Path.cwd())
