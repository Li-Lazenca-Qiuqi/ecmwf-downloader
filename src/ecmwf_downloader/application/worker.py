"""Process-independent scheduler and CDS download worker."""

from __future__ import annotations

import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
from typing import Optional
from uuid import uuid4

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider, DownloadCancelled, ProviderError

logger = logging.getLogger(__name__)


class DownloadEngine:
    def __init__(self, container: AppContainer):
        self.container = container

    def execute(self, task_id: str, account: dict) -> None:
        task = self.container.tasks.get(task_id)
        if task is None:
            return
        target = Path(task.output_path)
        part = Path(f"{target}.part")
        if target.exists() and not self._overwrite_allowed(task):
            self.container.tasks_repository.transition(
                task_id,
                TaskStatus.FAILED,
                error_message=f"目标文件已存在: {target}",
            )
            return

        monitor_stop = threading.Event()
        monitor = threading.Thread(
            target=self._monitor_file,
            args=(task_id, part, monitor_stop),
            name=f"progress-{task_id[:8]}",
            daemon=True,
        )
        try:
            part.parent.mkdir(parents=True, exist_ok=True)
            if part.exists():
                part.unlink()
            monitor.start()
            provider = CDSProvider(account)
            provider.download(
                dataset_id=task.dataset_id,
                request_payload=task.request_payload,
                target=part,
                cancel_check=lambda: self._cancel_requested(task_id),
            )
            monitor_stop.set()
            monitor.join(timeout=2)
            if self._cancel_requested(task_id):
                if part.exists():
                    part.unlink()
                current = self.container.tasks.get(task_id)
                if current and current.status == TaskStatus.CANCELLING:
                    self.container.tasks_repository.transition(task_id, TaskStatus.CANCELLED)
                return
            if not part.exists():
                raise ProviderError("CDS 下载完成但未生成文件")
            os.replace(part, target)
            size = target.stat().st_size
            self.container.tasks_repository.update_progress(
                task_id, downloaded_bytes=size, total_bytes=size, progress=100
            )
            self.container.tasks_repository.finish_completed(task_id)
            self.container.accounts.record_success(account["id"])
        except DownloadCancelled:
            monitor_stop.set()
            monitor.join(timeout=2)
            if part.exists():
                part.unlink()
            current = self.container.tasks.get(task_id)
            if current and current.status == TaskStatus.CANCELLING:
                self.container.tasks_repository.transition(task_id, TaskStatus.CANCELLED)
        except Exception as exc:
            monitor_stop.set()
            monitor.join(timeout=2)
            if part.exists():
                try:
                    part.unlink()
                except OSError:
                    logger.warning("无法清理临时文件: %s", part)
            logger.exception("任务 %s 下载失败", task_id)
            self.container.accounts.record_failure(account["id"], str(exc))
            try:
                self.container.tasks_repository.finish_failure(task_id, str(exc))
            except (KeyError, ValueError):
                logger.exception("任务 %s 写入失败状态失败", task_id)

    def _overwrite_allowed(self, task) -> bool:
        # The request-level flag is persisted in the repository, while the
        # public TaskData intentionally does not expose it as a secret.
        with self.container.database.session() as session:
            from ecmwf_downloader.infrastructure.db import TaskRow

            row = session.get(TaskRow, task.id)
            return bool(row and row.overwrite)

    def _cancel_requested(self, task_id: str) -> bool:
        task = self.container.tasks.get(task_id)
        return bool(task and (task.cancel_requested or task.status == TaskStatus.CANCELLING))

    def _monitor_file(self, task_id: str, path: Path, stop: threading.Event) -> None:
        last_size = -1
        while not stop.wait(0.75):
            try:
                size = path.stat().st_size if path.exists() else 0
                if size != last_size:
                    self.container.tasks_repository.update_progress(
                        task_id, downloaded_bytes=size, total_bytes=None, progress=None
                    )
                    last_size = size
            except OSError:
                continue


class DownloadScheduler:
    LEASE_NAME = "download-scheduler"

    def __init__(
        self,
        container: AppContainer,
        *,
        max_workers: Optional[int] = None,
        poll_interval: Optional[float] = None,
    ):
        self.container = container
        self.max_workers = max_workers or container.settings.download.max_workers
        self.poll_interval = poll_interval or container.settings.download.poll_interval
        self.owner_id = f"scheduler-{uuid4()}"
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._executor: Optional[ThreadPoolExecutor] = None
        self._active: dict[str, Future] = {}
        self._lock = threading.RLock()
        self.engine = DownloadEngine(container)

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._active)

    def start(self) -> bool:
        if self.is_running:
            return True
        if not self.container.lease_repository.acquire(self.LEASE_NAME, self.owner_id):
            return False
        recovered_ids = self.container.tasks_repository.recover_stale()
        for task_id in recovered_ids:
            task = self.container.tasks.get(task_id)
            if task is None:
                continue
            part = Path(f"{task.output_path}.part")
            try:
                if part.exists():
                    part.unlink()
            except OSError:
                logger.warning("无法清理遗留临时文件: %s", part)
        self._stop.clear()
        self._executor = ThreadPoolExecutor(max_workers=self.max_workers, thread_name_prefix="ecmwf-worker")
        self._thread = threading.Thread(target=self._loop, name="ecmwf-scheduler", daemon=True)
        self._thread.start()
        return True

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=max(2.0, self.poll_interval * 4))
        self._thread = None
        if self._executor:
            self._executor.shutdown(wait=False, cancel_futures=False)
            self._executor = None
        self.container.lease_repository.release(self.LEASE_NAME, self.owner_id)

    def _loop(self) -> None:
        try:
            while not self._stop.is_set():
                if not self.container.lease_repository.renew(self.LEASE_NAME, self.owner_id):
                    logger.error("调度器租约丢失，停止消费队列")
                    return
                with self._lock:
                    active_ids = list(self._active)
                for task_id in active_ids:
                    self.container.tasks_repository.renew_task_lease(task_id, self.owner_id)
                self._reap_finished()
                self._fill_slots()
                self._stop.wait(self.poll_interval)
        finally:
            self._reap_finished()

    def _reap_finished(self) -> None:
        with self._lock:
            finished = [task_id for task_id, future in self._active.items() if future.done()]
            for task_id in finished:
                future = self._active.pop(task_id)
                try:
                    future.result()
                except Exception:
                    logger.exception("Worker 未处理异常: %s", task_id)

    def _fill_slots(self) -> None:
        if self._executor is None:
            return
        while self.active_count < self.max_workers:
            account = self.container.accounts.next_available()
            if account is None:
                return
            task = self.container.tasks_repository.claim_next(self.owner_id)
            if task is None:
                return
            self.container.tasks_repository.set_account(task.id, account["id"])
            future = self._executor.submit(self.engine.execute, task.id, account)
            with self._lock:
                self._active[task.id] = future
