"""Application use cases; no Textual/FastAPI/Typer dependencies."""

from __future__ import annotations

from pathlib import Path
import json
import re
import threading
from typing import Any, Callable, Optional
from uuid import uuid4

from ecmwf_downloader.application.request_builder import PlannedTask, RequestBuilder
from ecmwf_downloader.application.request_compiler import compile_request
from ecmwf_downloader.config import AppSettings, NetworkProxySettings, public_service_url, service_url
from ecmwf_downloader.domain.models import AccountData, AccountStatus, SplitStrategy, TaskData, TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider
from ecmwf_downloader.infrastructure.mirrors import FILE_MIRROR_IDS
from ecmwf_downloader.infrastructure.repositories import (
    AccountStateRepository,
    TaskRepository,
    TemplateRepository,
)
from ecmwf_downloader.infrastructure.secrets import SecretStore


class TaskService:
    def __init__(self, settings: AppSettings, tasks: TaskRepository, accounts: AccountService):
        self.settings = settings
        self.tasks = tasks
        self.accounts = accounts
        self.builder = RequestBuilder()
        self.datasets = None

    def prepare_request(self, dataset_id, request_payload, schema_revision, editor_values, split_strategy):
        if schema_revision is None:
            if editor_values is not None:
                raise ValueError('编辑值需要对应的字段定义版本，请重新获取字段')
            return request_payload
        schema = self.datasets.by_revision(dataset_id, schema_revision)
        if split_strategy.value not in schema['capabilities']['split_strategies']:
            raise ValueError('当前数据集不支持此拆分方式')
        values = editor_values if editor_values is not None else request_payload
        compiled = compile_request(schema, values, wire=editor_values is None).checked()
        if editor_values is not None and json.dumps(compiled, sort_keys=True) != json.dumps(request_payload, sort_keys=True):
            raise ValueError('请求参数与当前编辑值不一致，请重新预览')
        return compiled

    def plan(
        self,
        *,
        dataset_id: str,
        request_payload: dict[str, Any],
        split_strategy: SplitStrategy = SplitStrategy.NONE,
        split_count: int | None = None,
        warnings: Optional[list[str]] = None,
        schema_revision: Optional[str] = None,
        editor_values: Optional[dict[str, Any]] = None,
    ) -> list[PlannedTask]:
        return self.builder.build(
            dataset_id=dataset_id,
            payload=self.prepare_request(dataset_id, request_payload, schema_revision, editor_values, split_strategy),
            strategy=split_strategy,
            split_count=split_count,
            warnings=warnings,
        )

    def preview(self, *, dataset_id: str, **options) -> list[dict[str, Any]]:
        plans = self.plan(dataset_id=dataset_id, **options)
        return [
            {
                "index": index,
                "dataset_id": dataset_id,
                "request_payload": plan.payload,
                "label": plan.label,
            }
            for index, plan in enumerate(plans, start=1)
        ]

    def create(
        self,
        *,
        dataset_id: str,
        request_payload: dict[str, Any],
        split_strategy: SplitStrategy = SplitStrategy.NONE,
        split_count: int | None = None,
        max_retries: Optional[int] = None,
        name: Optional[str] = None,
        account_ids: list[str] | None = None,
        schema_revision: Optional[str] = None,
        editor_values: Optional[dict[str, Any]] = None,
    ) -> list[TaskData]:
        plans = self.plan(
            dataset_id=dataset_id,
            request_payload=request_payload,
            schema_revision=schema_revision,
            editor_values=editor_values,
            split_strategy=split_strategy,
            split_count=split_count,
        )
        if account_ids is not None:
            if dataset_id in FILE_MIRROR_IDS:
                raise ValueError('镜像请求无需选择 CDS 账号')
            if not account_ids or len(account_ids) > len(plans) or len(set(account_ids)) != len(account_ids):
                raise ValueError('请选择账号，所选账号数不能超过请求份数')
            active_ids = {account['id'] for account in self.accounts.active_accounts()}
            if not set(account_ids) <= active_ids:
                raise ValueError('所选账号已不可用，请重新选择')
        return self.tasks.create_batch(
            dataset_id=dataset_id,
            items=[(plan.payload, plan.label) for plan in plans],
            name=(name or "").strip() or dataset_id,
            split_strategy=split_strategy,
            max_retries=max_retries if max_retries is not None else self.settings.requests.max_retries,
            account_ids=account_ids or (),
        )

    def get(self, task_id: str) -> Optional[TaskData]:
        return self.tasks.get(task_id)

    def list(self, **kwargs):
        return self.tasks.list(**kwargs)

    def batch(self, batch_id: str):
        return self.tasks.list_batch(batch_id)

    def summary(self):
        return self.tasks.summary()

    def cancel(self, task_id: str):
        return self.tasks.request_cancel(task_id)

    def retry(self, task_id: str):
        return self.tasks.retry(task_id)

    def refresh(self, task_id: str):
        return self.tasks.request_refresh(task_id)

    def attach(self, task_id: str, remote_id: str):
        if not re.fullmatch(r'[A-Za-z0-9_-]{1,255}', remote_id):
            raise ValueError('远端请求 ID 格式无效')
        task = self.tasks.get(task_id)
        if task is None:
            raise KeyError('请求不存在')
        if task.status != TaskStatus.SUBMISSION_UNKNOWN:
            raise ValueError('仅提交结果不明确的请求可关联远端 ID')
        account = self.datasets_account(task.account_id)
        CDSProvider(account, network=self.settings.network_proxy).verify_request(
            remote_id, task.dataset_id, task.request_payload,
        )
        return self.tasks.attach_remote(task_id, remote_id)

    def delete(self, task_id: str):
        return self.tasks.delete(task_id)


class AccountService:
    def __init__(
        self,
        secrets: SecretStore,
        states: AccountStateRepository,
        auto_disable_threshold: int = 5,
        *,
        network: Callable[[], NetworkProxySettings | None] = lambda: None,
    ):
        self.secrets = secrets
        self.states = states
        self.auto_disable_threshold = auto_disable_threshold
        self._network = network
        self._cursor = 0
        self._cursor_lock = threading.Lock()

    def list(self) -> list[AccountData]:
        state = self.states.snapshot()
        today_usage = self.states.today_usage()
        busy_accounts = self.states.busy_account_ids()
        result = []
        for account in self.secrets.accounts():
            account_id = str(account.get("id", ""))
            row = state.get(account_id)
            status = AccountStatus(row.status if row else account.get("status", "active"))
            result.append(
                AccountData(
                    id=account_id,
                    email=str(account.get("email", "")),
                    url=public_service_url(str(account.get("url", "https://cds.climate.copernicus.eu/api"))),
                    status=status,
                    is_busy=account_id in busy_accounts,
                    used_count=row.used_count if row else 0,
                    today_used_count=today_usage.get(account_id, 0),
                    fail_count=row.fail_count if row else 0,
                    last_used=row.last_used if row else None,
                    last_error="上次 CDS 操作失败，请检查账号权限与网络。" if row and row.last_error else None,
                )
            )
        return result

    def add(self, *, email: str, key: str, url: str, account_id: Optional[str] = None) -> AccountData:
        account_id = account_id or str(uuid4())
        self.secrets.upsert_account({"id": account_id, "email": email, "key": key, "url": service_url(url)})
        self.states.set_status(account_id, "active")
        return next(item for item in self.list() if item.id == account_id)

    def delete(self, account_id: str) -> bool:
        return self.secrets.delete_account(account_id)

    def set_status(self, account_id: str, status: AccountStatus) -> AccountData:
        if not self.secrets.get_account(account_id):
            raise KeyError(f"账号不存在: {account_id}")
        self.states.set_status(account_id, status.value)
        return next(item for item in self.list() if item.id == account_id)

    def active_accounts(self) -> list[dict[str, Any]]:
        state = self.states.snapshot()
        accounts = []
        for account in self.secrets.accounts(include_keys=True):
            row = state.get(str(account.get("id", "")))
            status = row.status if row else account.get("status", "active")
            if status == AccountStatus.ACTIVE.value:
                accounts.append(account)
        return sorted(accounts, key=lambda account: account['id'])

    def next_available(self, accounts: list[dict[str, Any]] | None = None) -> Optional[dict[str, Any]]:
        candidates = self.active_accounts() if accounts is None else accounts
        if not candidates:
            return None
        with self._cursor_lock:
            selected = candidates[self._cursor % len(candidates)]
            self._cursor += 1
        return selected

    def record_success(self, account_id: str) -> None:
        self.states.mark_success(account_id)

    def record_failure(self, account_id: str, message: str) -> None:
        self.states.mark_failure(account_id, message, threshold=self.auto_disable_threshold)

    def test(self, account_id: str) -> tuple[bool, str]:
        account = self.secrets.get_account(account_id)
        if not account:
            raise KeyError(f"账号不存在: {account_id}")
        return CDSProvider(account, network=self._network()).check_connection()


class TemplateService:
    def __init__(self, templates: TemplateRepository):
        self.templates = templates

    def list(self):
        return self.templates.list()

    def save(self, name: str, payload: dict[str, Any]):
        return self.templates.save(name, payload)

    def get(self, template_id: str):
        return self.templates.get(template_id)

    def delete(self, template_id: str):
        return self.templates.delete(template_id)
