from pathlib import Path
from datetime import datetime, timedelta, timezone

import pytest

from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import DownloadScheduler
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.db import TaskRow
from ecmwf_downloader.infrastructure.repositories import LeaseRepository


@pytest.fixture
def container(tmp_path: Path):
    return AppContainer(AppSettings(database_path=tmp_path / "db.sqlite3", config_dir=tmp_path / "config"))


def test_task_transitions_write_events(container):
    task = container.tasks.create(dataset_id="test", request_payload={"x": 1})[0]
    assert task.status == TaskStatus.PENDING
    queued = container.tasks.enqueue(task.id)
    assert queued.status == TaskStatus.QUEUED
    cancelled = container.tasks.cancel(task.id)
    assert cancelled.status == TaskStatus.CANCELLED
    events = container.tasks_repository.events_after(0)
    assert [event["event_type"] for event in events] == [
        "task.created",
        "task.status_changed",
        "task.status_changed",
    ]


def test_invalid_transition_is_rejected(container):
    task = container.tasks.create(dataset_id="test", request_payload={})[0]
    with pytest.raises(ValueError, match="非法状态转换"):
        container.tasks_repository.transition(task.id, TaskStatus.COMPLETED)


def test_secrets_are_masked_from_account_listing(container):
    account = container.accounts.add(email="test@example.com", key="secret", url="https://example.invalid")
    assert account.email == "test@example.com"
    assert all("key" not in item.model_dump() for item in container.accounts.list())
    assert (container.settings.config_dir / "secrets.yaml").stat().st_mode & 0o777 == 0o600


def test_scheduler_recovers_stale_task_and_removes_part_file(container, tmp_path: Path):
    task = container.tasks.create(
        dataset_id="test",
        request_payload={},
        output_dir=tmp_path / "downloads",
    )[0]
    part = Path(f"{task.output_path}.part")
    part.parent.mkdir(parents=True, exist_ok=True)
    part.write_bytes(b"stale")
    with container.database.session() as session:
        row = session.get(TaskRow, task.id)
        assert row is not None
        row.status = TaskStatus.RUNNING.value
        row.lease_expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    scheduler = DownloadScheduler(container, poll_interval=0.02)
    assert scheduler.start()
    scheduler.stop()
    recovered = container.tasks.get(task.id)
    assert recovered is not None and recovered.status == TaskStatus.QUEUED
    assert not part.exists()


def test_scheduler_lease_allows_only_one_owner(tmp_path: Path):
    from ecmwf_downloader.infrastructure.db import Database

    database = Database(tmp_path / "db.sqlite3")
    database.create_schema()
    first = LeaseRepository(database)
    second = LeaseRepository(database)
    assert first.acquire("download-scheduler", "owner-a")
    assert not second.acquire("download-scheduler", "owner-b")
    first.release("download-scheduler", "owner-a")
    assert second.acquire("download-scheduler", "owner-b")


def test_retry_resets_backoff_counters(container):
    task = container.tasks.create(dataset_id="test", request_payload={})[0]
    container.tasks.enqueue(task.id)
    claimed = container.tasks_repository.claim_next("worker")
    assert claimed is not None
    failed = container.tasks_repository.finish_failure(task.id, "temporary")
    assert failed.status == TaskStatus.RETRY_WAIT
    container.tasks_repository.transition(task.id, TaskStatus.RUNNING, worker_id="worker")
    container.tasks_repository.transition(task.id, TaskStatus.FAILED, error_message="final")
    retried = container.tasks.retry(task.id, enqueue=False)
    assert retried.status == TaskStatus.PENDING
    assert retried.retry_count == 0
