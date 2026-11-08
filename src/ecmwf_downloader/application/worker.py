"""单一请求队列：提交、轮询和交付结果元数据，不传输文件。"""
from __future__ import annotations
import logging
import threading
from concurrent.futures import ThreadPoolExecutor, wait
from uuid import uuid4
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider, ProviderError, SubmissionRejected, SubmissionUncertain
from ecmwf_downloader.infrastructure.mirrors import FILE_MIRROR_IDS, MirrorProvider

logger = logging.getLogger(__name__)

class RequestEngine:
    def __init__(self, container):
        self.container = container

    def execute(self, task_id):
        tasks = self.container.tasks_repository
        task = tasks.get(task_id)
        if task is None:
            return
        submission_id = None
        mirror = task.dataset_id in FILE_MIRROR_IDS
        try:
            if mirror:
                if task.status == TaskStatus.CANCELLING:
                    tasks.finish_cancelled(task_id)
                else:
                    assets = MirrorProvider().results(task.dataset_id, task.request_payload)
                    tasks.apply_remote(task_id, 'successful', assets, self.container.settings.requests.poll_interval)
                return
            account = self.container.secrets.get_account(task.account_id) if task.account_id else None
            if not account:
                raise ProviderError('提交账号已不可用，请恢复原账号；不会改用其他账号查询。')
            provider = CDSProvider(account)
            if task.status == TaskStatus.SUBMITTING:
                submission_id = provider.submit(task.dataset_id, task.request_payload)
                tasks.record_submission(task_id, submission_id, self.container.settings.requests.poll_interval)
            elif task.status == TaskStatus.CANCELLING:
                if not task.remote_request_id:
                    tasks.finish_cancelled(task_id)
                    return
                provider.cancel(task.remote_request_id)
                tasks.finish_cancelled(task_id)
            else:
                status, assets = provider.inspect(task.remote_request_id)
                tasks.apply_remote(task_id, status, assets, self.container.settings.requests.poll_interval,
                                   remote_id=task.remote_request_id)
        except SubmissionUncertain as exc:
            tasks.submission_failed(task_id, str(exc), uncertain=True)
        except Exception as exc:
            message = str(exc) if isinstance(exc, ProviderError) else '请求操作失败，请检查后台连接或结果元数据。'
            if task.status == TaskStatus.SUBMITTING:
                if submission_id:
                    tasks.record_submission(task_id, submission_id, self.container.settings.requests.poll_interval)
                else:
                    tasks.submission_failed(task_id, message, uncertain=not mirror and not isinstance(exc, ProviderError),
                                            rejected=isinstance(exc, SubmissionRejected))
            else:
                tasks.query_failed(task_id, message)

class RequestScheduler:
    LEASE_NAME = "request-scheduler"
    def __init__(self, container: AppContainer, *, max_workers=None, poll_interval=None):
        self.container = container
        self._max_workers = max_workers
        self._poll_interval = poll_interval
        self.owner_id = 'scheduler-' + str(uuid4())
        self._stop = threading.Event()
        self._thread = None
        self._executor = None
        self._active = {}
        self._lock = threading.RLock()
        self.engine = RequestEngine(container)

    @property
    def max_workers(self):
        return self._max_workers or self.container.settings.requests.max_workers

    @property
    def is_running(self):
        return bool(self._thread and self._thread.is_alive())

    @property
    def active_count(self):
        with self._lock:
            return len(self._active)

    def start(self):
        if self.is_running:
            return True
        if not self.container.lease_repository.acquire(self.LEASE_NAME, self.owner_id):
            return False
        self.container.tasks_repository.recover_stale()
        self._stop.clear()
        self._executor = ThreadPoolExecutor(max_workers=32, thread_name_prefix='ecmwf-request')
        self._thread = threading.Thread(target=self._loop, name='ecmwf-request-scheduler', daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop.set()
        if self._thread:
            self._thread.join()
        with self._lock:
            pending = list(self._active.values())
        # 网络操作退出并持久化结果前持续续租，避免关停期间被其他进程重复领取。
        while pending:
            _, remaining = wait(pending, timeout=1)
            pending = list(remaining)
            self.container.lease_repository.renew(self.LEASE_NAME, self.owner_id)
            for task_id in list(self._active):
                self.container.tasks_repository.renew_task_lease(task_id, self.owner_id)
        if self._executor:
            self._executor.shutdown(wait=True)
        self._reap_finished()
        self.container.lease_repository.release(self.LEASE_NAME, self.owner_id)
        self._thread = None
        self._executor = None

    def _loop(self):
        while not self._stop.is_set():
            if not self.container.lease_repository.renew(self.LEASE_NAME, self.owner_id):
                logger.error('请求调度租约丢失，停止领取新操作')
                return
            for task_id in list(self._active):
                self.container.tasks_repository.renew_task_lease(task_id, self.owner_id)
            self._reap_finished()
            # 运行中也恢复后来才过期的旧租约，不仅在启动时扫描。
            self.container.tasks_repository.recover_stale()
            self._fill_slots()
            self._stop.wait(self._poll_interval or 0.25)

    def _reap_finished(self):
        with self._lock:
            done = [task_id for task_id, future in self._active.items() if future.done()]
            for task_id in done:
                future = self._active.pop(task_id)
                if future.exception():
                    logger.error('请求 %s 后台操作异常，等待租约恢复', task_id)

    def _fill_slots(self):
        while not self._stop.is_set() and self.active_count < self.max_workers:
            account = self.container.accounts.next_available()
            task = self.container.tasks_repository.claim_next(
                self.owner_id, account_id=account['id'] if account else None,
                mirror_ids=FILE_MIRROR_IDS, exclude_ids=set(self._active), lease_name=self.LEASE_NAME)
            if task is None:
                return
            with self._lock:
                self._active[task.id] = self._executor.submit(self.engine.execute, task.id)
