"""Transactional repositories for tasks, events, leases and templates."""

from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, time, timedelta, timezone
from typing import Any, Callable, Iterable, Optional
from uuid import uuid4

from sqlalchemy import case, func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import aliased, contains_eager

from ecmwf_downloader.domain.models import (
    ACTIVE_STATUSES,
    ResultAsset,
    SplitStrategy,
    TaskBatch,
    TaskData,
    TaskStatus,
    can_transition,
)
from ecmwf_downloader.infrastructure.db import (
    AccountStateRow,
    Database,
    RequestBatchItemRow,
    RequestSubmissionAccountRow,
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
    def __init__(self, database: Database, retry_delays=None):
        self.database = database
        self.retry_delays = tuple(retry_delays or (5, 15, 60))

    @staticmethod
    def _to_data(row):
        data = {name: (json_loads(row.request_payload) if name == 'request_payload'
                       else json.loads(row.results) if name == 'results'
                       else getattr(row, name)) for name in TaskData.model_fields if name not in {'batch', 'submission_account_id'}}
        for name, value in data.items():
            if isinstance(value, datetime) and value.tzinfo is None:
                data[name] = value.replace(tzinfo=timezone.utc)
        batch = TaskBatch.model_validate(row.batch, from_attributes=True) if row.batch else None
        assigned = row.submission_account.account_id if row.submission_account else None
        return TaskData(**data, batch=batch, submission_account_id=assigned)

    @staticmethod
    def _event(session, *, event_type, task_id, payload, now):
        session.add(TaskEventRow(task_id=task_id, event_type=event_type,
                                 payload=json_dumps(payload), created_at=now))

    def _row(self, session, task_id):
        row = session.get(TaskRow, task_id)
        if row is None:
            raise KeyError(f"请求不存在: {task_id}")
        return row

    def _change(self, session, row, status, error=None, *, used_account_id=None):
        previous = TaskStatus(row.status)
        if status != previous and not can_transition(previous, status):
            raise ValueError(f"非法状态转换: {previous.value} -> {status.value}")
        row.status = status.value
        row.updated_at = _utc_now()
        row.error_message = error
        row.version += 1
        if status not in ACTIVE_STATUSES:
            row.worker_id = None
            row.lease_expires_at = None
        if status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED, TaskStatus.EXPIRED}:
            row.completed_at = row.updated_at
        if previous != status or error:
            payload = {"from": previous.value, "status": status.value, "error_message": error}
            if status == TaskStatus.COMPLETED:
                payload["used_account_id"] = used_account_id
            self._event(session, event_type="task.status_changed", task_id=row.id, payload=payload, now=row.updated_at)

    def create_batch(self, *, dataset_id, items, name, split_strategy, max_retries, account_ids=()):
        batch_id = str(uuid4())
        with self.database.session(immediate=True) as session:
            now = _utc_now()
            rows = []
            for position, (request_payload, title) in enumerate(items, start=1):
                row = TaskRow(id=str(uuid4()), dataset_id=dataset_id,
                              request_payload=json_dumps(request_payload), title=title,
                              status=TaskStatus.QUEUED.value, split_strategy=split_strategy.value,
                              max_retries=max_retries, created_at=now, updated_at=now,
                              batch=RequestBatchItemRow(batch_id=batch_id, name=name,
                                                        position=position, total=len(items)))
                if account_ids:
                    row.submission_account = RequestSubmissionAccountRow(
                        account_id=account_ids[(position - 1) % len(account_ids)],
                    )
                rows.append(row)
                session.add(row)
                self._event(session, event_type="task.created", task_id=row.id,
                            payload={"status": row.status}, now=now)
            session.flush()
            return [self._to_data(row) for row in rows]

    def get(self, task_id):
        with self.database.session() as session:
            row = session.get(TaskRow, task_id)
            return self._to_data(row) if row else None

    def list(self, *, status=None, search=None, limit=50, offset=0):
        with self.database.session() as session:
            predicates = []
            if status:
                predicates.append(TaskRow.status == status.value)
            if search:
                needle = '%' + search + '%'
                predicates.append(or_(TaskRow.id.like(needle), TaskRow.title.like(needle),
                                      TaskRow.dataset_id.like(needle), TaskRow.remote_request_id.like(needle),
                                      TaskRow.batch.has(RequestBatchItemRow.name.like(needle))))
            query = select(TaskRow).outerjoin(TaskRow.batch).options(contains_eager(TaskRow.batch)).where(*predicates)
            total = session.scalar(select(func.count()).select_from(TaskRow).where(*predicates))
            rows = session.scalars(query.order_by(
                TaskRow.created_at.desc(), RequestBatchItemRow.batch_id,
                RequestBatchItemRow.position, TaskRow.id,
            ).limit(limit).offset(offset))
            return [self._to_data(row) for row in rows], int(total or 0)

    def summary(self):
        with self.database.session() as session:
            counts = dict(session.execute(select(TaskRow.status, func.count()).group_by(TaskRow.status)).all())
            return {"total": sum(counts.values()), "by_status": counts,
                    "completed": counts.get(TaskStatus.COMPLETED.value, 0)}

    def claim_next(self, worker_id, *, account_id=None, available_account_ids=None, mirror_ids=frozenset(),
                   exclude_ids=(), lease_seconds=60, lease_name=None):
        now = _utc_now()
        if available_account_ids is None:
            available_account_ids = (account_id,) if account_id else ()
        with self.database.session(immediate=True) as session:
            if lease_name is not None:
                lease = session.get(SchedulerLeaseRow, lease_name)
                if lease is None or lease.owner_id != worker_id:
                    return None
                expires = lease.expires_at.replace(tzinfo=timezone.utc) if lease.expires_at.tzinfo is None else lease.expires_at
                if expires <= now:
                    return None
            active = [status.value for status in ACTIVE_STATUSES if status != TaskStatus.SUBMITTING]
            assigned_account = RequestSubmissionAccountRow.account_id
            queued_eligible = or_(
                TaskRow.dataset_id.in_(mirror_ids),
                assigned_account.in_(available_account_ids),
                assigned_account.is_(None) & (account_id is not None),
            )
            due = select(TaskRow).outerjoin(TaskRow.batch).outerjoin(TaskRow.submission_account).options(
                contains_eager(TaskRow.batch), contains_eager(TaskRow.submission_account),
            ).where(
                TaskRow.worker_id.is_(None), TaskRow.id.not_in(exclude_ids),
                or_(TaskRow.next_retry_at.is_(None), TaskRow.next_retry_at <= now),
                or_(TaskRow.status.in_(active), (TaskRow.status == 'queued') & queued_eligible),
            )
            row = session.scalar(due.order_by(
                case((TaskRow.status == 'cancelling', 0), (TaskRow.status == 'queued', 2), else_=1),
                TaskRow.next_retry_at.asc(), TaskRow.created_at.asc(), RequestBatchItemRow.batch_id,
                RequestBatchItemRow.position, TaskRow.id,
            ).limit(1))
            if row is None:
                return None
            if row.status == 'queued':
                if row.submission_account:
                    row.account_id = row.submission_account.account_id
                else:
                    row.account_id = None if row.dataset_id in mirror_ids else account_id
                row.started_at = row.started_at or now
                self._change(session, row, TaskStatus.SUBMITTING)
            row.worker_id = worker_id
            row.lease_expires_at = now + timedelta(seconds=lease_seconds)
            return self._to_data(row)

    def record_submission(self, task_id, remote_id, poll_interval):
        if not remote_id:
            raise ValueError('远端未返回请求 ID')
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status not in {'submitting', 'submission_unknown', 'cancelling'}:
                return self._to_data(row)
            row.remote_request_id = remote_id
            row.remote_status = 'accepted'
            row.worker_id = None
            row.lease_expires_at = None
            row.next_retry_at = _utc_now() + timedelta(seconds=0 if row.cancel_requested else poll_interval)
            self._change(session, row, TaskStatus.CANCELLING if row.cancel_requested else TaskStatus.ACCEPTED)
            return self._to_data(row)

    def apply_remote(self, task_id, remote_status, assets, poll_interval, *, remote_id=None):
        parsed = [ResultAsset.model_validate(asset).model_dump(mode='json') for asset in assets]
        if remote_status == 'successful' and not parsed:
            raise ValueError('远端结果为空，尚无可用文件链接')
        states = {'accepted': TaskStatus.ACCEPTED, 'running': TaskStatus.RUNNING,
                  'successful': TaskStatus.COMPLETED, 'failed': TaskStatus.FAILED,
                  'rejected': TaskStatus.FAILED, 'dismissed': TaskStatus.CANCELLED,
                  'deleted': TaskStatus.EXPIRED, 'expired': TaskStatus.EXPIRED}
        if remote_status not in states:
            raise ValueError('远端返回了无法识别的作业状态')
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status not in {state.value for state in ACTIVE_STATUSES}:
                return self._to_data(row)
            if remote_id is not None and row.remote_request_id != remote_id:
                return self._to_data(row)
            row.worker_id = None
            row.lease_expires_at = None
            row.checked_at = _utc_now()
            row.retry_count = 0
            if row.cancel_requested:
                row.next_retry_at = _utc_now()
                return self._to_data(row)
            row.remote_status = remote_status
            target = states[remote_status]
            if target == TaskStatus.FAILED:
                self._account_failure(session, row, '远端请求失败')
            used_account_id = row.account_id if target == TaskStatus.COMPLETED and not row.account_success_recorded else None
            row.results = json_dumps(parsed) if target == TaskStatus.COMPLETED else '[]'
            row.next_retry_at = _utc_now() + timedelta(seconds=poll_interval) if target in ACTIVE_STATUSES else None
            self._change(session, row, target,
                         '远端请求失败，请查看官方请求详情；可重新提交。' if target == TaskStatus.FAILED else None,
                         used_account_id=used_account_id)
            if used_account_id:
                account = session.get(AccountStateRow, used_account_id)
                if account is None:
                    account = AccountStateRow(account_id=used_account_id, used_count=0, fail_count=0, status='active')
                    session.add(account)
                account.used_count += 1
                account.fail_count = 0
                account.last_used = row.updated_at
                account.last_error = None
                row.account_success_recorded = True
            return self._to_data(row)

    @staticmethod
    def _account_failure(session, row, message):
        if not row.account_id:
            return
        account = session.get(AccountStateRow, row.account_id)
        if account is None:
            account = AccountStateRow(account_id=row.account_id, used_count=0, fail_count=0, status='active')
            session.add(account)
        account.fail_count += 1
        account.last_error = message
        if account.fail_count >= 5:
            account.status = 'disabled'

    def submission_failed(self, task_id, message, *, uncertain, rejected=False):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            target = TaskStatus.SUBMISSION_UNKNOWN if uncertain else TaskStatus.FAILED
            if rejected and row.status != 'failed':
                row.remote_status = 'rejected'
                self._account_failure(session, row, message)
            self._change(session, row, target, message)
            return self._to_data(row)

    def query_failed(self, task_id, message):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status not in {status.value for status in ACTIVE_STATUSES}:
                return self._to_data(row)
            row.worker_id = None
            row.lease_expires_at = None
            row.retry_count += 1
            if row.retry_count > row.max_retries:
                self._change(session, row, TaskStatus.FAILED,
                             message + ' 查询重试已用尽；重试将继续处理原远端请求。')
                row.next_retry_at = None
            else:
                delay = self.retry_delays[min(row.retry_count - 1, len(self.retry_delays) - 1)]
                row.next_retry_at = _utc_now() + timedelta(seconds=delay)
                row.error_message = message
                row.updated_at = _utc_now()
                self._event(session, event_type='task.query_retry', task_id=row.id,
                            payload={'retry_count': row.retry_count, 'status': row.status}, now=row.updated_at)
            return self._to_data(row)

    def request_cancel(self, task_id):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status in {'cancelled', 'cancelling'}:
                return self._to_data(row)
            if row.status == 'queued':
                self._change(session, row, TaskStatus.CANCELLED)
            elif row.status in {'submitting', 'accepted', 'running', 'refreshing'} or (
                    row.status == 'failed' and row.remote_request_id and row.remote_status not in {'failed', 'rejected'}):
                row.cancel_requested = True
                row.retry_count = 0
                row.next_retry_at = None
                self._change(session, row, TaskStatus.CANCELLING)
            else:
                raise ValueError('此请求当前不能取消；提交结果不明确时须先关联远端 ID')
            return self._to_data(row)

    def finish_cancelled(self, task_id):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            row.results = '[]'
            row.remote_status = 'dismissed'
            row.next_retry_at = None
            self._change(session, row, TaskStatus.CANCELLED)
            return self._to_data(row)

    def retry(self, task_id):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status not in {'failed', 'expired', 'cancelled'}:
                raise ValueError('只能重试失败请求或明确重新提交失效/取消的请求')
            resume = row.status == 'failed' and row.remote_request_id and row.remote_status not in {'failed','rejected','dismissed'}
            row.retry_count = 0
            row.next_retry_at = None
            row.completed_at = None
            if resume:
                self._change(session, row, TaskStatus.CANCELLING if row.cancel_requested else TaskStatus.ACCEPTED)
            else:
                self._event(session, event_type='task.resubmitted', task_id=row.id,
                            payload={'previous_request_id': row.remote_request_id}, now=_utc_now())
                row.account_success_recorded = False
                row.remote_request_id = None
                row.remote_status = None
                row.results = '[]'
                row.cancel_requested = False
                row.started_at = None
                self._change(session, row, TaskStatus.QUEUED)
            return self._to_data(row)

    def request_refresh(self, task_id):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status == 'completed':
                self._change(session, row, TaskStatus.REFRESHING)
            elif not (row.status in {'accepted', 'running'} and row.remote_request_id and not row.cancel_requested):
                raise ValueError('仅远端排队、处理中的请求或就绪结果可刷新状态')
            row.next_retry_at = None
            return self._to_data(row)

    def attach_remote(self, task_id, remote_id):
        with self.database.session(immediate=True) as session:
            row = self._row(session, task_id)
            if row.status != 'submission_unknown':
                raise ValueError('仅提交结果不明确的请求可关联远端 ID')
            row.remote_request_id = remote_id
            row.remote_status = 'accepted'
            row.next_retry_at = None
            self._change(session, row, TaskStatus.CANCELLING if row.cancel_requested else TaskStatus.ACCEPTED)
            return self._to_data(row)

    def renew_task_lease(self, task_id, worker_id, lease_seconds=60):
        with self.database.session(immediate=True) as session:
            row = session.get(TaskRow, task_id)
            if row is None or row.worker_id != worker_id:
                return False
            row.lease_expires_at = _utc_now() + timedelta(seconds=lease_seconds)
            return True

    def recover_stale(self):
        now = _utc_now()
        recovered = []
        with self.database.session(immediate=True) as session:
            rows = session.scalars(select(TaskRow).where(
                TaskRow.worker_id.is_not(None),
                or_(TaskRow.lease_expires_at.is_(None), TaskRow.lease_expires_at <= now)))
            for row in rows:
                row.worker_id = None
                row.lease_expires_at = None
                if not row.remote_request_id and row.status in {'submitting', 'cancelling'}:
                    self._change(session, row, TaskStatus.SUBMISSION_UNKNOWN, '进程中断，提交结果不明确；请在官方请求页核实并关联远端 ID。')
                row.next_retry_at = None
                recovered.append(row.id)
        return recovered

    def delete(self, task_id):
        with self.database.session(immediate=True) as session:
            row = session.get(TaskRow, task_id)
            if row is None:
                return False
            if row.status in {'queued','submission_unknown'} | {state.value for state in ACTIVE_STATUSES}:
                raise ValueError('先结束或核实请求，再删除本地记录')
            if row.status == 'failed' and row.remote_request_id and row.remote_status not in {'failed','rejected','dismissed','expired'}:
                raise ValueError('远端请求仍可能运行，请先继续监视或取消后删除')
            session.delete(row)
            self._event(session, event_type='task.deleted', task_id=task_id, payload={}, now=_utc_now())
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
            with self.database.session(immediate=True) as session:
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
            with self.database.session(immediate=True) as session:
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
        with self.database.session(immediate=True) as session:
            row = session.get(SchedulerLeaseRow, name)
            if not row or row.owner_id != owner_id:
                return False
            row.heartbeat_at = now
            row.expires_at = now + timedelta(seconds=lease_seconds)
            return True

    def release(self, name: str, owner_id: str) -> None:
        with self.database.session(immediate=True) as session:
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

    def busy_account_ids(self) -> set[str]:
        with self.database.session() as session:
            return set(session.scalars(
                select(TaskRow.account_id).distinct().where(
                    TaskRow.account_id.is_not(None),
                    TaskRow.status.in_([status.value for status in ACTIVE_STATUSES]),
                )
            ))

    def today_usage(self) -> dict[str, int]:
        today = _utc_now().astimezone().date()
        start = datetime.combine(today, time.min).astimezone(timezone.utc)
        end = datetime.combine(today + timedelta(days=1), time.min).astimezone(timezone.utc)
        used_account = func.json_extract(TaskEventRow.payload, '$.used_account_id')
        completions = (
            TaskEventRow.event_type == 'task.status_changed',
            func.json_extract(TaskEventRow.payload, '$.status') == TaskStatus.COMPLETED.value,
            TaskEventRow.created_at >= start,
            TaskEventRow.created_at < end,
        )

        # 旧事件只可回溯仍保留账号绑定的最后一次提交。
        history = aliased(TaskEventRow)
        last_resubmission = (
            select(func.max(history.id))
            .where(history.task_id == TaskRow.id, history.event_type == 'task.resubmitted')
            .correlate(TaskRow).scalar_subquery()
        )
        first_completion = (
            select(func.min(history.id))
            .where(history.task_id == TaskRow.id, history.event_type == 'task.status_changed',
                   func.json_extract(history.payload, '$.status') == TaskStatus.COMPLETED.value,
                   history.id > func.coalesce(last_resubmission, 0))
            .correlate(TaskRow).scalar_subquery()
        )
        legacy = (
            select(TaskRow.account_id, func.count())
            .select_from(TaskEventRow)
            .join(TaskRow, TaskRow.id == TaskEventRow.task_id)
            .where(*completions, func.json_type(TaskEventRow.payload, '$.used_account_id').is_(None),
                   TaskRow.account_id.is_not(None), TaskRow.account_success_recorded,
                   TaskEventRow.id == first_completion)
            .group_by(TaskRow.account_id)
        )
        with self.database.session() as session:
            counts = Counter(dict(session.execute(
                select(used_account, func.count()).where(*completions, used_account.is_not(None)).group_by(used_account)
            ).all()))
            counts.update(dict(session.execute(legacy).all()))
            return dict(counts)

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
        with self.database.session(immediate=True) as session:
            row = session.scalar(select(RequestTemplateRow).where(RequestTemplateRow.name == name))
            if row is not None and payload.get('kind') == 'ecmwf-request-preset-v1':
                if json_loads(row.payload).get('kind') != 'ecmwf-request-preset-v1':
                    raise ValueError('此名称已用于其他模板，请更换预设名称')
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
