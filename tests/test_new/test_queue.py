from pathlib import Path
import threading
import time

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import DownloadEngine, DownloadScheduler
from ecmwf_downloader.config import AppSettings, DownloadSettings
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider
from ecmwf_downloader.infrastructure.db import TaskRow
from ecmwf_downloader.interfaces.cli.app import app
from ecmwf_downloader.interfaces.http.app import create_app


@pytest.fixture
def container(tmp_path):
    value = AppContainer(AppSettings(
        database_path=tmp_path / 'db.sqlite3', config_dir=tmp_path / 'config',
        download=DownloadSettings(output_dir=tmp_path / 'downloads', max_workers=1),
    ))
    yield value
    value.database.engine.dispose()


def test_preview_does_not_create_and_split_tasks_are_queued(container):
    request = dict(dataset_id='test', request_payload={'year': [2023, 2024]}, split_strategy='year')
    from ecmwf_downloader.domain.models import SplitStrategy
    request['split_strategy'] = SplitStrategy.YEAR
    assert len(container.tasks.preview(**request)) == 2
    assert container.tasks.list()[1] == 0
    tasks = container.tasks.create(**request)
    assert len(tasks) == 2 and all(task.status == TaskStatus.QUEUED for task in tasks)
    assert all(event['payload']['status'] == 'queued' for event in container.tasks_repository.events_after())


def test_api_rejects_deferred_creation_and_preserves_old_true_flag(container):
    with TestClient(create_app(container, with_worker=False)) as client:
        request = {'dataset_id': 'test', 'request_payload': {}}
        assert client.post('/api/v1/tasks', json={**request, 'enqueue': False}).status_code == 422
        assert container.tasks.list()[1] == 0
        assert client.post('/api/v1/tasks', json={**request, 'enqueue': True}).json()['items'][0]['status'] == 'queued'
        summary = client.get('/api/v1/summary').json()
        assert summary['available_accounts'] == 0
        assert summary['scheduler_running'] is False
        assert summary['max_workers'] is None


def test_cli_creates_queued_without_enqueue_option(container):
    import json
    runner = CliRunner()
    args = ['--config-dir', str(container.settings.config_dir), '--database', str(container.settings.database_path)]
    result = runner.invoke(app, [*args, 'task', 'create', '--dataset', 'test', '--output-dir', str(container.settings.download.output_dir), '--json'])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)[0]['status'] == 'queued'
    help_result = runner.invoke(app, [*args, 'task', 'create', '--help'], color=False)
    assert '--enqueue' not in help_result.output


def test_cancelled_waiting_task_is_not_claimed_or_retried(container):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    assert container.tasks.cancel(task.id).status == TaskStatus.CANCELLED
    assert container.tasks.cancel(task.id).status == TaskStatus.CANCELLED
    assert container.tasks_repository.claim_next('worker') is None
    assert container.tasks_repository.finish_failure(task.id, 'late error').status == TaskStatus.CANCELLED
    assert container.tasks.get(task.id).retry_count == 0


def test_cancel_during_retry_wait_prevents_claim(container):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    container.tasks_repository.claim_next('worker')
    assert container.tasks_repository.finish_failure(task.id, 'temporary').status == TaskStatus.RETRY_WAIT
    assert container.tasks.cancel(task.id).status == TaskStatus.CANCELLED
    assert container.tasks_repository.claim_next('worker') is None


@pytest.mark.parametrize('fails', [False, True])
def test_running_cancel_does_not_publish_or_count_as_account_failure(container, monkeypatch, fails):
    account = container.accounts.add(email='test@example.invalid', key='fake-key', url='https://example.invalid')
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    container.tasks_repository.claim_next('worker')
    def download(self, *, target, **kwargs):
        target.write_bytes(b'partial')
        container.tasks.cancel(task.id)
        if fails:
            raise RuntimeError('transport ended after cancellation')
        return target
    monkeypatch.setattr(CDSProvider, 'download', download)
    DownloadEngine(container).execute(task.id, container.secrets.get_account(account.id))
    finished = container.tasks.get(task.id)
    assert finished.status == TaskStatus.CANCELLED and finished.retry_count == 0
    assert not Path(task.output_path).exists()
    assert not Path(f'{task.output_path}.part').exists()
    assert container.accounts.list()[0].fail_count == 0


def test_cancel_wins_before_final_publication(container, monkeypatch):
    account = container.accounts.add(email='test@example.invalid', key='fake-key', url='https://example.invalid')
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    container.tasks_repository.claim_next('worker')
    def download(self, *, target, **kwargs):
        target.write_bytes(b'data')
        return target
    original = container.tasks_repository.finish_completed
    def finish(task_id, publish=None):
        container.tasks.cancel(task_id)
        return original(task_id, publish=publish)
    monkeypatch.setattr(CDSProvider, 'download', download)
    monkeypatch.setattr(container.tasks_repository, 'finish_completed', finish)
    DownloadEngine(container).execute(task.id, container.secrets.get_account(account.id))
    assert container.tasks.get(task.id).status == TaskStatus.CANCELLED
    assert not Path(task.output_path).exists()
    assert not Path(f'{task.output_path}.part').exists()


def test_single_queue_respects_capacity_and_cancels_queued_task(container, monkeypatch):
    container.accounts.add(email='test@example.invalid', key='fake-key', url='https://example.invalid')
    entered = threading.Event()
    release = threading.Event()
    called = []
    def download(self, *, target, **kwargs):
        called.append(target.name)
        entered.set()
        assert release.wait(5)
        target.write_bytes(b'data')
        return target
    monkeypatch.setattr(CDSProvider, 'download', download)
    first = container.tasks.create(dataset_id='test', request_payload={}, filename='first.nc')[0]
    second = container.tasks.create(dataset_id='test', request_payload={}, filename='second.nc')[0]
    scheduler = DownloadScheduler(container, poll_interval=0.01)
    assert scheduler.start()
    try:
        assert entered.wait(5)
        assert container.tasks.get(first.id).status == TaskStatus.RUNNING
        assert container.tasks.get(second.id).status == TaskStatus.QUEUED
        container.tasks.cancel(second.id)
        release.set()
        deadline = time.monotonic() + 5
        while scheduler.active_count and time.monotonic() < deadline:
            time.sleep(0.01)
        assert len(called) == 1
        assert container.tasks.get(first.id).status == TaskStatus.COMPLETED
        assert container.tasks.get(second.id).status == TaskStatus.CANCELLED
    finally:
        release.set()
        scheduler.stop()


def test_existing_pending_is_not_automatically_started(container):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    with container.database.session() as session:
        session.get(TaskRow, task.id).status = TaskStatus.PENDING.value
    reopened = AppContainer(container.settings)
    try:
        assert reopened.tasks.get(task.id).status == TaskStatus.PENDING
        assert reopened.tasks_repository.claim_next('worker') is None
        assert reopened.tasks.enqueue(task.id).status == TaskStatus.QUEUED
    finally:
        reopened.database.engine.dispose()


def test_cancel_after_claim_before_worker_starts_finishes_cancelled(container, monkeypatch):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    container.tasks_repository.claim_next('worker')
    container.tasks.cancel(task.id)
    def unexpected_download(*args, **kwargs):
        pytest.fail('已取消的任务不应进入下载适配器')
    monkeypatch.setattr(CDSProvider, 'download', unexpected_download)
    DownloadEngine(container).execute(task.id, {'id': 'unused', 'key': 'fake'})
    assert container.tasks.get(task.id).status == TaskStatus.CANCELLED


def test_existing_target_fails_without_overwrite_or_retry(container):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    target = Path(task.output_path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(b'existing')
    container.tasks_repository.claim_next('worker')
    DownloadEngine(container).execute(task.id, {'id': 'unused', 'key': 'fake'})
    assert container.tasks.get(task.id).status == TaskStatus.FAILED
    assert container.tasks.get(task.id).retry_count == 0
    assert target.read_bytes() == b'existing'
