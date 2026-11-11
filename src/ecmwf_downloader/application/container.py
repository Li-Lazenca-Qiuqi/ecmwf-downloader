"""Composition root used by CLI, FastAPI and the scheduler."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ecmwf_downloader.application.ai import AIService
from ecmwf_downloader.application.datasets import DatasetService
from ecmwf_downloader.application.services import AccountService, TaskService, TemplateService
from ecmwf_downloader.config import (
    AppSettings,
    NetworkProxySettings,
    PublicAISettings,
    SettingsError,
    SettingsIOError,
    load_settings,
    parse_app_config,
    validate_app_config,
)
from ecmwf_downloader.infrastructure.db import Database
from ecmwf_downloader.infrastructure.repositories import (
    AccountStateRepository,
    LeaseRepository,
    TaskRepository,
    TemplateRepository,
)
from ecmwf_downloader.infrastructure.secrets import SecretStore, SecretStoreError
from ecmwf_downloader.infrastructure.yaml_file import atomic_write_bytes, atomic_write_yaml, file_write_lock


class AppContainer:
    def __init__(self, settings: AppSettings | None = None, *, config_path: Path | None = None):
        if settings is None:
            config_path = config_path or Path("config/app.yaml")
            settings = load_settings(config_dir=config_path.parent, config_path=config_path)
        self.settings = settings.resolve_relative_paths()
        self.config_path = (config_path or self.settings.config_dir / "app.yaml").resolve()
        self.settings.config_dir.mkdir(parents=True, exist_ok=True)
        self.database = Database(self.settings.database_path)
        self.database.create_schema()
        self.secrets = SecretStore(self.settings.config_dir / "secrets.yaml")
        self.tasks_repository = TaskRepository(
            self.database,
            retry_delays=self.settings.requests.retry_delays,
        )
        self.lease_repository = LeaseRepository(self.database)
        self.account_state_repository = AccountStateRepository(self.database)
        self.template_repository = TemplateRepository(self.database)
        self.tasks = TaskService(self.settings, self.tasks_repository)
        self.accounts = AccountService(self.secrets, self.account_state_repository, network=self._network_settings)
        self.templates = TemplateService(self.template_repository)
        self.datasets = DatasetService(network=self._network_settings)
        self.tasks.datasets = self.datasets
        self.tasks.datasets_account = self.secrets.get_account
        self.ai = AIService(self.settings, self.secrets)

    def _network_settings(self) -> NetworkProxySettings:
        return self.settings.network_proxy

    def update_settings(self, values: dict[str, Any], *, ai_key: str | None = None) -> AppSettings:
        """先验证完整配置，保存成功后才更新进程内设置。"""
        if set(values) - {"requests", "ai", "network_proxy"}:
            raise SettingsError("只能修改 requests、ai 或 network_proxy 非敏感设置")
        if any(not isinstance(section, dict) for section in values.values()):
            raise SettingsError("设置分组必须是对象")
        if "ai" in values:
            if {"api_key", "key", "token", "secret"} & values["ai"].keys():
                raise SettingsError("AI 凭据必须写入 config/secrets.yaml，不得写入 app.yaml")
            try:
                ai = PublicAISettings.model_validate(values["ai"]).model_dump(exclude_unset=True)
            except ValidationError:
                raise SettingsError("AI 设置无效，请检查字段、类型、范围和服务地址。") from None
            values = {**values, "ai": ai}

        path = self.config_path
        try:
            with file_write_lock(path):
                previous = path.read_bytes() if path.exists() else None
                runtime = self.settings.model_dump(mode="json")
                data = parse_app_config(previous) if previous is not None else runtime.copy()
                for section, section_values in values.items():
                    current = data.get(section, {})
                    if not isinstance(current, dict):
                        raise SettingsError("应用配置分组必须是对象。")
                    data[section] = {**current, **section_values}
                    # 独立进程写入的其他值在重启时读取，本进程只应用本次更新。
                    runtime[section] = {**runtime[section], **section_values}
                validate_app_config(data)
                updated = validate_app_config(runtime)
                if values.get('ai', {}).get('enabled') or ai_key is not None:
                    stored_ai = self.secrets.ai_config()
                    enabled = updated.ai.get('enabled', stored_ai.get('enabled', False))
                    key = stored_ai.get('api_key') if ai_key is None else ai_key
                    if enabled and not key:
                        raise SettingsError('请填写 API Key，或关闭 AI 服务后保存。')
                atomic_write_yaml(path, data)
                if ai_key is not None:
                    try:
                        self.secrets.update_ai({"api_key": ai_key})
                    except SecretStoreError:
                        # 两个文件分开存储，凭据保存失败时恢复原应用配置。
                        try:
                            if previous is None:
                                path.unlink()
                            else:
                                atomic_write_bytes(path, previous)
                        except OSError:
                            raise SettingsIOError("凭据保存失败，应用配置也未能恢复，请检查存储。") from None
                        raise
                self.tasks_repository.retry_delays = tuple(updated.requests.retry_delays)
                self.tasks.settings = updated
                self.ai.settings = updated
                self.settings = updated
        except OSError:
            raise SettingsIOError("无法保存应用配置，请检查权限与磁盘空间。") from None
        return updated
