"""Application use cases; no Textual/FastAPI/Typer dependencies."""

from __future__ import annotations

from pathlib import Path
import threading
from typing import Any, Optional
from uuid import uuid4

from ecmwf_downloader.application.request_builder import RequestBuilder
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.models import AccountData, AccountStatus, SplitStrategy, TaskData, TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider
from ecmwf_downloader.infrastructure.repositories import (
    AccountStateRepository,
    TaskRepository,
    TemplateRepository,
)
from ecmwf_downloader.infrastructure.secrets import SecretStore


class TaskService:
    def __init__(self, settings: AppSettings, tasks: TaskRepository):
        self.settings = settings
        self.tasks = tasks
        self.builder = RequestBuilder()

    def preview(
        self,
        *,
        dataset_id: str,
        request_payload: dict[str, Any],
        output_dir: Optional[Path] = None,
        split_strategy: SplitStrategy = SplitStrategy.NONE,
        filename: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        plans = self.builder.build(
            dataset_id=dataset_id,
            payload=request_payload,
            output_dir=output_dir or self.settings.download.output_dir,
            strategy=split_strategy,
            filename=filename,
        )
        return [
            {
                "index": index,
                "dataset_id": dataset_id,
                "request_payload": plan.payload,
                "filename": plan.filename,
                "output_path": str(plan.output_path),
            }
            for index, plan in enumerate(plans, start=1)
        ]

    def create(
        self,
        *,
        dataset_id: str,
        request_payload: dict[str, Any],
        output_dir: Optional[Path] = None,
        split_strategy: SplitStrategy = SplitStrategy.NONE,
        filename: Optional[str] = None,
        max_retries: Optional[int] = None,
        overwrite: Optional[bool] = None,
        enqueue: bool = False,
    ) -> list[TaskData]:
        plans = self.builder.build(
            dataset_id=dataset_id,
            payload=request_payload,
            output_dir=output_dir or self.settings.download.output_dir,
            strategy=split_strategy,
            filename=filename,
        )
        tasks = [
            self.tasks.create(
                dataset_id=dataset_id,
                request_payload=plan.payload,
                filename=plan.filename,
                output_path=str(plan.output_path),
                split_strategy=split_strategy,
                max_retries=max_retries if max_retries is not None else self.settings.download.max_retries,
                overwrite=overwrite if overwrite is not None else self.settings.download.overwrite,
            )
            for plan in plans
        ]
        if enqueue:
            tasks = [self.tasks.enqueue(task.id) for task in tasks]
        return tasks

    def get(self, task_id: str) -> Optional[TaskData]:
        return self.tasks.get(task_id)

    def list(self, **kwargs):
        return self.tasks.list(**kwargs)

    def summary(self):
        return self.tasks.summary()

    def enqueue(self, task_id: str):
        return self.tasks.enqueue(task_id)

    def enqueue_many(self, task_ids: list[str]):
        return self.tasks.enqueue_many(task_ids)

    def cancel(self, task_id: str):
        return self.tasks.request_cancel(task_id)

    def retry(self, task_id: str, enqueue: bool = True):
        return self.tasks.retry(task_id, enqueue=enqueue)

    def delete(self, task_id: str):
        return self.tasks.delete(task_id)


class AccountService:
    def __init__(
        self,
        secrets: SecretStore,
        states: AccountStateRepository,
        auto_disable_threshold: int = 5,
    ):
        self.secrets = secrets
        self.states = states
        self.auto_disable_threshold = auto_disable_threshold
        self._cursor = 0
        self._cursor_lock = threading.Lock()

    def list(self) -> list[AccountData]:
        state = self.states.snapshot()
        result = []
        for account in self.secrets.accounts():
            account_id = str(account.get("id", ""))
            row = state.get(account_id)
            status = AccountStatus(row.status if row else account.get("status", "active"))
            result.append(
                AccountData(
                    id=account_id,
                    email=str(account.get("email", "")),
                    url=str(account.get("url", "https://cds.climate.copernicus.eu/api")),
                    status=status,
                    used_count=row.used_count if row else 0,
                    fail_count=row.fail_count if row else 0,
                    last_used=row.last_used if row else None,
                    last_error=row.last_error if row else None,
                )
            )
        return result

    def add(self, *, email: str, key: str, url: str, account_id: Optional[str] = None) -> AccountData:
        account_id = account_id or str(uuid4())
        self.secrets.upsert_account({"id": account_id, "email": email, "key": key, "url": url})
        self.states.set_status(account_id, "active")
        return next(item for item in self.list() if item.id == account_id)

    def delete(self, account_id: str) -> bool:
        return self.secrets.delete_account(account_id)

    def set_status(self, account_id: str, status: AccountStatus) -> AccountData:
        if not self.secrets.get_account(account_id):
            raise KeyError(f"账号不存在: {account_id}")
        self.states.set_status(account_id, status.value)
        return next(item for item in self.list() if item.id == account_id)

    def next_available(self) -> Optional[dict[str, Any]]:
        state = self.states.snapshot()
        candidates = []
        for account in self.secrets.accounts(include_keys=True):
            account_id = str(account.get("id", ""))
            row = state.get(account_id)
            status = row.status if row else account.get("status", "active")
            if status == AccountStatus.ACTIVE.value:
                candidates.append((row.used_count if row else 0, account_id, account))
        candidates.sort(key=lambda item: item[1])
        if not candidates:
            return None
        with self._cursor_lock:
            selected = candidates[self._cursor % len(candidates)]
            self._cursor += 1
        return selected[2]

    def record_success(self, account_id: str) -> None:
        self.states.mark_success(account_id)

    def record_failure(self, account_id: str, message: str) -> None:
        self.states.mark_failure(account_id, message, threshold=self.auto_disable_threshold)

    def test(self, account_id: str) -> tuple[bool, str]:
        account = self.secrets.get_account(account_id)
        if not account:
            raise KeyError(f"账号不存在: {account_id}")
        return CDSProvider(account).check_connection()


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
