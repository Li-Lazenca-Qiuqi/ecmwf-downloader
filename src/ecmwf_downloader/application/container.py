"""Composition root used by CLI, FastAPI and the scheduler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from ecmwf_downloader.application.ai import AIService
from ecmwf_downloader.application.datasets import DatasetService
from ecmwf_downloader.application.services import AccountService, TaskService, TemplateService
from ecmwf_downloader.config import AppSettings, load_settings
from ecmwf_downloader.infrastructure.db import Database
from ecmwf_downloader.infrastructure.repositories import (
    AccountStateRepository,
    LeaseRepository,
    TaskRepository,
    TemplateRepository,
)
from ecmwf_downloader.infrastructure.secrets import SecretStore


class AppContainer:
    def __init__(self, settings: AppSettings | None = None):
        self.settings = (settings or load_settings()).resolve_relative_paths(Path.cwd())
        self.settings.config_dir.mkdir(parents=True, exist_ok=True)
        self.database = Database(self.settings.database_path)
        self.database.create_schema()
        self.secrets = SecretStore(self.settings.config_dir / "secrets.yaml")
        self.tasks_repository = TaskRepository(
            self.database,
            retry_delays=self.settings.download.retry_delays,
        )
        self.lease_repository = LeaseRepository(self.database)
        self.account_state_repository = AccountStateRepository(self.database)
        self.template_repository = TemplateRepository(self.database)
        self.tasks = TaskService(self.settings, self.tasks_repository)
        self.accounts = AccountService(self.secrets, self.account_state_repository)
        self.templates = TemplateService(self.template_repository)
        self.datasets = DatasetService()
        self.ai = AIService(self.settings, self.secrets)

    def update_settings(self, values: dict[str, Any]) -> AppSettings:
        """Persist allow-listed non-secret settings and reload them."""
        allowed = {"download", "ai"}
        if set(values) - allowed:
            raise ValueError("只能修改 download 或 ai 非敏感设置")
        path = self.settings.config_dir / "app.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
        data = data if isinstance(data, dict) else {}
        for section, section_values in values.items():
            if not isinstance(section_values, dict):
                raise ValueError(f"设置分组必须是对象: {section}")
            if section == "ai" and {"api_key", "key", "token", "secret"} & set(section_values):
                raise ValueError("AI 凭据必须写入 config/secrets.yaml，不得写入 app.yaml")
            data[section] = {**(data.get(section) or {}), **section_values}
        path.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")
        reloaded = load_settings(config_dir=self.settings.config_dir, config_path=path)
        reloaded.config_dir = self.settings.config_dir
        reloaded.database_path = self.settings.database_path
        self.settings = reloaded
        self.tasks.settings = self.settings
        self.ai.settings = self.settings
        self.tasks_repository.retry_delays = tuple(self.settings.download.retry_delays) or (5.0,)
        return self.settings
