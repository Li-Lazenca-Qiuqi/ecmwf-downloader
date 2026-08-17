"""Transactional repositories for tasks, events, leases and templates."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Iterable, Optional
from uuid import uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError

from ecmwf_downloader.domain.models import (
    SplitStrategy,
    TaskData,
    TaskStatus,
    can_transition,
)
from ecmwf_downloader.infrastructure.db import (
    AccountStateRow,
    Database,
    RequestTemplateRow,
    SchedulerLeaseRow,
    TaskEventRow,
    TaskRow,
    json_dumps,
    json_loads,
)


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class TaskRepository:
    def __init__(self, database: Database, retry_delays: Optional[Iterable[float]] = None):
        self.database = database
        configured_delays = tuple(float(delay) for delay in (retry_delays or (5.0, 15.0, 60.0)))
        self.retry_delays = configured_delays or (5.0,)

    @staticmethod
    def _to_data(row: TaskRow) -> TaskData:
        return TaskData(
            id=row.id,
            dataset_id=row.dataset_id,
            request_payload=json_loads(row.request_payload),
            filename=row.filename,
            output_path=row.output_path,
            status=TaskStatus(row.status),
            split_strategy=SplitStrategy(row.split_strategy),
            progress=row.progress,
            downloaded_bytes=row.downloaded_bytes,
            total_bytes=row.total_bytes,
            retry_count=row.retry_count,
            max_retries=row.max_retries,
            next_retry_at=row.next_retry_at,
            error_message=row.error_message,
            account_id=row.account_id,
            cancel_requested=row.cancel_requested,
            created_at=row.created_at,
            updated_at=row.updated_at,
            started_at=row.started_at,
            completed_at=row.completed_at,
        )

    @staticmethod
    def _event(
        session,
        *,
        event_type: str,
        task_id: Optional[str],
        payload: dict[str, Any],
        now: datetime,
    ) -> TaskEventRow:
        event = TaskEventRow(
            task_id=task_id,
            event_type=event_type,
            payload=json_dumps(payload),
            created_at=now,
        )
        session.add(event)
        return event

    def create(
        self,
        *,
        dataset_id: str,
        request_payload: dict[str, Any],
        filename: str,
        output_path: str,
        split_strategy: SplitStrategy,
        max_retries: int,
        overwrite: bool,
        task_id: Optional[str] = None,
    ) -> TaskData:
        now = _utc_now()
        row = TaskRow(
            id=task_id or str(uuid4()),
            dataset_id=dataset_id,
            request_payload=json_dumps(request_payload),
            filename=filename,
            output_path=output_path,
            status=TaskStatus.PENDING.value,
            split_strategy=split_strategy.value,
            max_retries=max_retries,
            overwrite=overwrite,
            created_at=now,
            updated_at=now,
        )
        with self.database.session() as session:
            session.add(row)
            self._event(
                session,
                event_type="task.created",
                task_id=row.id,
                payload={"status": row.status},
                now=now,
            )
        return self._to_data(row)

    def get(self, task_id: str) -> Optional[TaskData]:
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            return self._to_data(row) if row else None

    def list(
        self,
        *,
        status: Optional[TaskStatus] = None,
        search: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TaskData], int]:
        with self.database.session() as session:
            query = select(TaskRow)
            count_query = select(func.count()).select_from(TaskRow)
            if status:
                query = query.where(TaskRow.status == status.value)
                count_query = count_query.where(TaskRow.status == status.value)
            if search:
                needle = f"%{search}%"
                predicate = or_(
                    TaskRow.id.like(needle),
                    TaskRow.filename.like(needle),
                    TaskRow.dataset_id.like(needle),
                )
                query = query.where(predicate)
                count_query = count_query.where(predicate)
            query = query.order_by(TaskRow.created_at.desc()).limit(limit).offset(offset)
            rows = list(session.scalars(query))
            total = int(session.scalar(count_query) or 0)
            return [self._to_data(row) for row in rows], total

    def summary(self) -> dict[str, Any]:
        with self.database.session() as session:
            rows = session.execute(
                select(TaskRow.status, func.count()).group_by(TaskRow.status)
            ).all()
            counts = {str(status): int(count) for status, count in rows}
            total = sum(counts.values())
            completed = counts.get(TaskStatus.COMPLETED.value, 0)
            progress_values = session.scalars(
                select(TaskRow.progress).where(TaskRow.progress.is_not(None))
            )
            values = [float(value) for value in progress_values]
            return {
                "total": total,
                "by_status": counts,
                "completed": completed,
                "overall_progress": round(sum(values) / len(values), 2) if values else None,
            }

    def transition(
        self,
        task_id: str,
        target: TaskStatus,
        *,
        error_message: Optional[str] = None,
        next_retry_at: Optional[datetime] = None,
        worker_id: Optional[str] = None,
    ) -> TaskData:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                raise KeyError(f"任务不存在: {task_id}")
            current = TaskStatus(row.status)
            if not can_transition(current, target):
                raise ValueError(f"非法状态转换: {current.value} -> {target.value}")
            row.status = target.value
            row.updated_at = now
            row.version += 1
            row.error_message = error_message
            row.next_retry_at = next_retry_at
            if target == TaskStatus.RUNNING:
                row.started_at = row.started_at or now
                row.worker_id = worker_id
            if target in {
                TaskStatus.COMPLETED,
                TaskStatus.FAILED,
                TaskStatus.CANCELLED,
            }:
                row.completed_at = now
                row.worker_id = None
                row.lease_expires_at = None
            if target == TaskStatus.PENDING:
                row.cancel_requested = False
                row.account_id = None
                row.started_at = None
                row.completed_at = None
                row.progress = None
                row.downloaded_bytes = 0
                row.total_bytes = None
                row.retry_count = 0
                row.next_retry_at = None
            if target == TaskStatus.CANCELLING:
                row.cancel_requested = True
            if target in {TaskStatus.QUEUED, TaskStatus.RETRY_WAIT}:
                row.cancel_requested = False
            self._event(
                session,
                event_type="task.status_changed",
                task_id=task_id,
                payload={
                    "from": current.value,
                    "status": target.value,
                    "error_message": error_message,
                },
                now=now,
            )
            return self._to_data(row)

    def enqueue(self, task_id: str) -> TaskData:
        return self.transition(task_id, TaskStatus.QUEUED)

    def enqueue_many(self, task_ids: Iterable[str]) -> int:
        count = 0
        for task_id in task_ids:
            try:
                self.enqueue(task_id)
            except (KeyError, ValueError):
                continue
            count += 1
        return count

    def request_cancel(self, task_id: str) -> TaskData:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"任务不存在: {task_id}")
        if task.status in {TaskStatus.PENDING, TaskStatus.QUEUED, TaskStatus.RETRY_WAIT}:
            return self.transition(task_id, TaskStatus.CANCELLED)
        if task.status == TaskStatus.RUNNING:
            return self.transition(task_id, TaskStatus.CANCELLING)
        if task.status == TaskStatus.CANCELLING:
            return task
        raise ValueError(f"任务当前不可取消: {task.status.value}")

    def retry(self, task_id: str, *, enqueue: bool = True) -> TaskData:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"任务不存在: {task_id}")
        if task.status not in {TaskStatus.FAILED, TaskStatus.CANCELLED}:
            raise ValueError(f"只能重试失败或取消任务: {task.status.value}")
        self.transition(task_id, TaskStatus.PENDING)
        return self.enqueue(task_id) if enqueue else self.get(task_id)  # type: ignore[return-value]

    def update_progress(
        self,
        task_id: str,
        *,
        downloaded_bytes: int,
        total_bytes: Optional[int] = None,
        progress: Optional[float] = None,
    ) -> Optional[TaskData]:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            row.downloaded_bytes = max(0, int(downloaded_bytes))
            row.total_bytes = total_bytes
            row.progress = progress
            row.updated_at = now
            row.version += 1
            self._event(
                session,
                event_type="task.progress",
                task_id=task_id,
                payload={
                    "downloaded_bytes": row.downloaded_bytes,
                    "total_bytes": row.total_bytes,
                    "progress": row.progress,
                },
                now=now,
            )
            return self._to_data(row)

    def set_account(self, task_id: str, account_id: str) -> Optional[TaskData]:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return None
            row.account_id = account_id
            row.updated_at = now
            row.version += 1
            return self._to_data(row)

    def claim_next(self, worker_id: str, lease_seconds: int = 60) -> Optional[TaskData]:
        now = _utc_now()
        expires = now + timedelta(seconds=lease_seconds)
        with self.database.session() as session:
            candidates = list(
                session.scalars(
                    select(TaskRow)
                    .where(TaskRow.status.in_([TaskStatus.QUEUED.value, TaskStatus.RETRY_WAIT.value]))
                    .order_by(TaskRow.created_at.asc())
                    .limit(20)
                )
            )
            for row in candidates:
                if row.status == TaskStatus.RETRY_WAIT.value and row.next_retry_at:
                    retry_at = row.next_retry_at
                    if retry_at.tzinfo is None:
                        retry_at = retry_at.replace(tzinfo=timezone.utc)
                    if retry_at > now:
                        continue
                previous = row.status
                row.status = TaskStatus.RUNNING.value
                row.worker_id = worker_id
                row.lease_expires_at = expires
                row.started_at = row.started_at or now
                row.updated_at = now
                row.version += 1
                self._event(
                    session,
                    event_type="task.status_changed",
                    task_id=row.id,
                    payload={"from": previous, "status": "running", "worker_id": worker_id},
                    now=now,
                )
                return self._to_data(row)
            return None

    def renew_task_lease(self, task_id: str, worker_id: str, lease_seconds: int = 60) -> bool:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if not row or row.worker_id != worker_id or row.status not in {
                TaskStatus.RUNNING.value,
                TaskStatus.CANCELLING.value,
            }:
                return False
            row.lease_expires_at = now + timedelta(seconds=lease_seconds)
            row.updated_at = now
            return True

    def recover_stale(self) -> list[str]:
        now = _utc_now()
        recovered: list[str] = []
        with self.database.session() as session:
            rows = list(
                session.scalars(
                    select(TaskRow).where(
                        TaskRow.status.in_([
                            TaskStatus.RUNNING.value,
                            TaskStatus.CANCELLING.value,
                        ])
                    )
                )
            )
            for row in rows:
                expires = row.lease_expires_at
                if expires and expires.tzinfo is None:
                    expires = expires.replace(tzinfo=timezone.utc)
                if expires and expires > now:
                    continue
                previous = row.status
                row.status = (
                    TaskStatus.CANCELLED.value
                    if previous == TaskStatus.CANCELLING.value
                    else TaskStatus.QUEUED.value
                )
                row.worker_id = None
                row.lease_expires_at = None
                row.cancel_requested = False
                row.updated_at = now
                row.version += 1
                self._event(
                    session,
                    event_type="task.recovered",
                    task_id=row.id,
                    payload={"from": previous, "status": row.status},
                    now=now,
                )
                recovered.append(row.id)
        return recovered

    def finish_completed(self, task_id: str) -> TaskData:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"任务不存在: {task_id}")
        if task.status == TaskStatus.CANCELLING or task.cancel_requested:
            return self.transition(task_id, TaskStatus.CANCELLED)
        return self.transition(task_id, TaskStatus.COMPLETED)

    def finish_failure(self, task_id: str, message: str) -> TaskData:
        task = self.get(task_id)
        if task is None:
            raise KeyError(f"任务不存在: {task_id}")
        if task.status == TaskStatus.CANCELLING:
            return self.transition(task_id, TaskStatus.CANCELLED, error_message=message)
        if task.retry_count < task.max_retries:
            retry_count = task.retry_count + 1
            delay = self.retry_delays[min(retry_count - 1, len(self.retry_delays) - 1)]
            retry_at = _utc_now() + timedelta(seconds=delay)
            now = _utc_now()
            with self.database.session() as session:
                row = session.get(TaskRow, task_id)
                if row is None:
                    raise KeyError(f"任务不存在: {task_id}")
                row.retry_count = retry_count
                row.status = TaskStatus.RETRY_WAIT.value
                row.next_retry_at = retry_at
                row.error_message = message
                row.worker_id = None
                row.lease_expires_at = None
                row.updated_at = now
                row.version += 1
                self._event(
                    session,
                    event_type="task.retry_scheduled",
                    task_id=task_id,
                    payload={"status": row.status, "retry_count": retry_count, "next_retry_at": retry_at.isoformat()},
                    now=now,
                )
                return self._to_data(row)
        return self.transition(task_id, TaskStatus.FAILED, error_message=message)

    def delete(self, task_id: str) -> bool:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return False
            if row.status in {
                TaskStatus.QUEUED.value,
                TaskStatus.RUNNING.value,
                TaskStatus.RETRY_WAIT.value,
                TaskStatus.CANCELLING.value,
            }:
                raise ValueError("排队或运行中的任务必须先取消后删除")
            session.delete(row)
            self._event(
                session,
                event_type="task.deleted",
                task_id=task_id,
                payload={},
                now=now,
            )
            return True

    def events_after(self, event_id: int = 0, limit: int = 100) -> list[dict[str, Any]]:
        with self.database.session() as session:
            rows = list(
                session.scalars(
                    select(TaskEventRow)
                    .where(TaskEventRow.id > event_id)
                    .order_by(TaskEventRow.id.asc())
                    .limit(limit)
                )
            )
            return [
                {
                    "id": row.id,
                    "event_type": row.event_type,
                    "task_id": row.task_id,
                    "payload": json_loads(row.payload),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]


class LeaseRepository:
    def __init__(self, database: Database):
        self.database = database

    def acquire(self, name: str, owner_id: str, lease_seconds: int = 30) -> bool:
        now = _utc_now()
        expires = now + timedelta(seconds=lease_seconds)
        try:
            with self.database.session() as session:
                row = session.get(SchedulerLeaseRow, name)
                if row is None:
                    session.add(
                        SchedulerLeaseRow(
                            name=name,
                            owner_id=owner_id,
                            heartbeat_at=now,
                            expires_at=expires,
                        )
                    )
                    return True
                existing_expires = row.expires_at
                if existing_expires.tzinfo is None:
                    existing_expires = existing_expires.replace(tzinfo=timezone.utc)
                if row.owner_id != owner_id and existing_expires > now:
                    return False
                row.owner_id = owner_id
                row.heartbeat_at = now
                row.expires_at = expires
                return True
        except IntegrityError:
            # Two independent processes can both observe an empty lease table.
            # The losing insert is retried as a read after its transaction rolls
            # back, so it reports contention instead of leaking an SQL error.
            with self.database.session() as session:
                row = session.get(SchedulerLeaseRow, name)
                if row is None:
                    return False
                existing_expires = row.expires_at
                if existing_expires.tzinfo is None:
                    existing_expires = existing_expires.replace(tzinfo=timezone.utc)
                if row.owner_id == owner_id:
                    row.heartbeat_at = now
                    row.expires_at = expires
                    return True
                if existing_expires <= now:
                    row.owner_id = owner_id
                    row.heartbeat_at = now
                    row.expires_at = expires
                    return True
                return False

    def renew(self, name: str, owner_id: str, lease_seconds: int = 30) -> bool:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(SchedulerLeaseRow, name)
            if not row or row.owner_id != owner_id:
                return False
            row.heartbeat_at = now
            row.expires_at = now + timedelta(seconds=lease_seconds)
            return True

    def release(self, name: str, owner_id: str) -> None:
        with self.database.session() as session:
            row = session.get(SchedulerLeaseRow, name)
            if row and row.owner_id == owner_id:
                session.delete(row)


class AccountStateRepository:
    def __init__(self, database: Database):
        self.database = database

    def get_or_create(self, account_id: str) -> AccountStateRow:
        with self.database.session() as session:
            row = session.get(AccountStateRow, account_id)
            if row is None:
                row = AccountStateRow(account_id=account_id)
                session.add(row)
            return row

    def snapshot(self) -> dict[str, AccountStateRow]:
        with self.database.session() as session:
            rows = list(session.scalars(select(AccountStateRow)))
            return {row.account_id: row for row in rows}

    def mark_success(self, account_id: str) -> None:
        now = _utc_now()
        with self.database.session() as session:
            row = session.get(AccountStateRow, account_id) or AccountStateRow(account_id=account_id)
            row.used_count += 1
            row.fail_count = 0
            row.status = "active"
            row.last_used = now
            row.last_error = None
            session.add(row)

    def mark_failure(self, account_id: str, message: str, threshold: int = 5) -> None:
        with self.database.session() as session:
            row = session.get(AccountStateRow, account_id) or AccountStateRow(account_id=account_id)
            row.fail_count += 1
            row.last_error = message
            if row.fail_count >= threshold:
                row.status = "disabled"
            session.add(row)

    def set_status(self, account_id: str, status: str) -> None:
        with self.database.session() as session:
            row = session.get(AccountStateRow, account_id) or AccountStateRow(account_id=account_id)
            row.status = status
            session.add(row)


class TemplateRepository:
    def __init__(self, database: Database):
        self.database = database

    def list(self) -> list[dict[str, Any]]:
        with self.database.session() as session:
            rows = list(session.scalars(select(RequestTemplateRow).order_by(RequestTemplateRow.name)))
            return [
                {"id": row.id, "name": row.name, "payload": json_loads(row.payload), "updated_at": row.updated_at.isoformat()}
                for row in rows
            ]

    def save(self, name: str, payload: dict[str, Any]) -> dict[str, Any]:
        now = _utc_now()
        with self.database.session() as session:
            row = session.scalar(select(RequestTemplateRow).where(RequestTemplateRow.name == name))
            if row is None:
                row = RequestTemplateRow(id=str(uuid4()), name=name, payload=json_dumps(payload), created_at=now, updated_at=now)
                session.add(row)
            else:
                row.payload = json_dumps(payload)
                row.updated_at = now
            return {"id": row.id, "name": row.name, "payload": payload, "updated_at": now.isoformat()}

    def get(self, template_id: str) -> Optional[dict[str, Any]]:
        with self.database.session() as session:
            row = session.get(RequestTemplateRow, template_id)
            if not row:
                return None
            return {"id": row.id, "name": row.name, "payload": json_loads(row.payload), "updated_at": row.updated_at.isoformat()}

    def delete(self, template_id: str) -> bool:
        with self.database.session() as session:
            row = session.get(RequestTemplateRow, template_id)
            if not row:
                return False
            session.delete(row)
            return True
