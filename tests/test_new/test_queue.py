import json
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, update
from typer.testing import CliRunner
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import RequestEngine
from ecmwf_downloader.config import AppSettings, RequestSettings
from ecmwf_downloader.domain.models import SplitStrategy, TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider, ProviderError, SubmissionUncertain
from ecmwf_downloader.infrastructure import repositories
from ecmwf_downloader.infrastructure.db import TaskEventRow, TaskRow
from ecmwf_downloader.interfaces.http.app import create_app
from ecmwf_downloader.interfaces.cli.app import app

URL = 'https://files.example.test/result.nc?signature=private-link'
ASSETS = [{'url': URL, 'filename': 'result.nc', 'size': 0, 'content_type': 'application/x-netcdf'}]

@pytest.fixture
def container(tmp_path):
    value = AppContainer(AppSettings(database_path=tmp_path/'db', config_dir=tmp_path/'config',
                                    requests=RequestSettings(max_retries=1, retry_delays=[0])))
    value.accounts.add(email='test@example.invalid', key='private-key', url='https://example.invalid')
    yield value
    value.database.engine.dispose()

def claim(c):
    account = c.accounts.next_available()
    return c.tasks_repository.claim_next('test-worker', account_id=account['id'] if account else None)

def due(c, task_id):
    with c.database.session(immediate=True) as session:
        session.get(TaskRow, task_id).next_retry_at = None

def submitted(c, monkeypatch):
    task = c.tasks.create(dataset_id='test', request_payload={'year':['2024']})[0]
    assert claim(c).id == task.id
    monkeypatch.setattr(CDSProvider, 'submit', lambda *args: 'remote-1')
    RequestEngine(c).execute(task.id)
    assert c.tasks.get(task.id).remote_request_id == 'remote-1'
    due(c, task.id)
    return task

def test_end_to_end_request_links_and_events_do_not_contain_file_bytes(container, monkeypatch):
    calls = []
    def submit(*args):
        calls.append(1)
        return 'remote-1'
    monkeypatch.setattr(CDSProvider, 'submit', submit)
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    assert claim(container).status == TaskStatus.SUBMITTING
    engine = RequestEngine(container)
    engine.execute(task.id)
    for state in ['running','successful']:
        due(container, task.id)
        assert claim(container).id == task.id
        monkeypatch.setattr(CDSProvider, 'inspect', lambda *args: (state, ASSETS if state=='successful' else []))
        engine.execute(task.id)
    result = container.tasks.get(task.id)
    assert result.status == TaskStatus.COMPLETED and result.results[0].size == 0
    assert result.remote_request_id == 'remote-1' and len(calls)==1
    assert 'output_path' not in result.model_dump() and 'downloaded_bytes' not in result.model_dump()
    assert 'private-link' not in json.dumps(container.tasks_repository.events_after())
    assert container.accounts.list()[0].used_count == 1

def test_poll_errors_retry_existing_job_never_resubmit(container, monkeypatch):
    task = submitted(container, monkeypatch)
    monkeypatch.setattr(CDSProvider, 'submit', lambda *args: pytest.fail('重复提交'))
    def broken(*args): raise ProviderError('查询失败')
    monkeypatch.setattr(CDSProvider, 'inspect', broken)
    engine = RequestEngine(container)
    for _ in range(2):
        assert claim(container).id == task.id
        engine.execute(task.id)
    assert container.tasks.get(task.id).status == TaskStatus.FAILED
    resumed = container.tasks.retry(task.id)
    assert resumed.remote_request_id == 'remote-1' and resumed.status == TaskStatus.ACCEPTED
    assert claim(container).id == task.id
    monkeypatch.setattr(CDSProvider, 'inspect', lambda *args: ('successful', ASSETS))
    engine.execute(task.id)
    assert container.tasks.get(task.id).status == TaskStatus.COMPLETED

def test_uncertain_submission_not_retried_and_requires_matching_remote(container, monkeypatch):
    def uncertain(*args): raise SubmissionUncertain('待核实')
    monkeypatch.setattr(CDSProvider, 'submit', uncertain)
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    claim(container)
    RequestEngine(container).execute(task.id)
    assert container.tasks.get(task.id).status == TaskStatus.SUBMISSION_UNKNOWN
    assert claim(container) is None
    with pytest.raises(ValueError): container.tasks.retry(task.id)
    monkeypatch.setattr(CDSProvider, 'verify_request', lambda *args: None)
    attached = container.tasks.attach(task.id, 'known-remote')
    assert attached.remote_request_id == 'known-remote' and attached.status == TaskStatus.ACCEPTED
    with pytest.raises(ValueError): container.tasks.attach(task.id, '../bad')

def test_cancel_before_submit_thread_starts_does_not_contact_remote(container, monkeypatch):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    claim(container)
    container.tasks.cancel(task.id)
    monkeypatch.setattr(CDSProvider, 'submit', lambda *args: pytest.fail('取消后提交'))
    RequestEngine(container).execute(task.id)
    assert container.tasks.get(task.id).status == TaskStatus.CANCELLED

def test_cancel_during_submission_preserves_remote_id_then_confirms_cancel(container, monkeypatch):
    task = container.tasks.create(dataset_id='test', request_payload={})[0]
    claim(container)
    def submit(*args):
        container.tasks.cancel(task.id)
        return 'remote-cancel'
    monkeypatch.setattr(CDSProvider, 'submit', submit)
    engine = RequestEngine(container)
    engine.execute(task.id)
    current = container.tasks.get(task.id)
    assert current.status == TaskStatus.CANCELLING and current.remote_request_id == 'remote-cancel'
    called = []
    monkeypatch.setattr(CDSProvider, 'cancel', lambda _, rid: called.append(rid))
    claim(container)
    engine.execute(task.id)
    assert called == ['remote-cancel'] and container.tasks.get(task.id).status == TaskStatus.CANCELLED

def test_cancel_wins_over_ready_result(container, monkeypatch):
    task = submitted(container, monkeypatch)
    claim(container)
    container.tasks.cancel(task.id)
    result = container.tasks_repository.apply_remote(task.id, 'successful', ASSETS, 1, remote_id='remote-1')
    assert result.status == TaskStatus.CANCELLING and result.results == []
    assert container.accounts.list()[0].used_count == 0

def test_refresh_expiry_and_explicit_resubmission(container, monkeypatch):
    task = submitted(container, monkeypatch)
    claim(container)
    container.tasks_repository.apply_remote(task.id,'successful',ASSETS,1,remote_id='remote-1')
    assert container.tasks.refresh(task.id).status == TaskStatus.REFRESHING
    claim(container)
    monkeypatch.setattr(CDSProvider,'inspect',lambda *args:('expired',[]))
    RequestEngine(container).execute(task.id)
    expired = container.tasks.get(task.id)
    assert expired.status == TaskStatus.EXPIRED and expired.results == []
    assert claim(container) is None
    again = container.tasks.retry(task.id)
    assert again.status == TaskStatus.QUEUED and again.remote_request_id is None

def test_multiple_results_refresh_does_not_double_count_account(container, monkeypatch):
    task = submitted(container, monkeypatch)
    assets = [*ASSETS, {'url':'https://files.example.test/second.nc', 'size':42}]
    claim(container)
    container.tasks_repository.apply_remote(task.id,'successful',assets,1,remote_id='remote-1')
    container.tasks.refresh(task.id)
    claim(container)
    container.tasks_repository.apply_remote(task.id,'successful',assets,1,remote_id='remote-1')
    assert len(container.tasks.get(task.id).results)==2 and container.accounts.list()[0].used_count==1
    with TestClient(create_app(container, with_worker=False)) as client:
        assert len(client.get('/api/v1/tasks/'+task.id+'/links').json()['items'])==2

def test_account_busy_tracks_bound_active_requests(container):
    repo = container.tasks_repository
    account = container.accounts.list()[0]
    other = container.accounts.add(email='idle@example.invalid', key='fake', url='https://example.invalid')
    first, second = [container.tasks.create(dataset_id='test', request_payload={})[0] for _ in range(2)]

    with TestClient(create_app(container, with_worker=False)) as client:
        def expect_busy(expected):
            accounts = {item['id']: item for item in client.get('/api/v1/accounts').json()['items']}
            assert accounts[account.id]['is_busy'] is expected
            assert accounts[account.id]['status'] == 'active'
            assert accounts[other.id]['is_busy'] is False

        expect_busy(False)
        assert repo.claim_next('test-worker', account_id=account.id).id == first.id
        expect_busy(True)
        repo.record_submission(first.id, 'first', 60)
        expect_busy(True)
        repo.apply_remote(first.id, 'running', [], 60, remote_id='first')
        expect_busy(True)
        assert repo.claim_next('test-worker', account_id=account.id).id == second.id
        repo.record_submission(second.id, 'second', 60)
        repo.apply_remote(first.id, 'successful', ASSETS, 60, remote_id='first')
        expect_busy(True)
        container.tasks.cancel(second.id)
        expect_busy(True)
        repo.finish_cancelled(second.id)
        expect_busy(False)
        container.tasks.refresh(first.id)
        expect_busy(True)
        repo.apply_remote(first.id, 'expired', [], 60, remote_id='first')
        expect_busy(False)


def test_daily_cds_usage_uses_local_midnight_and_survives_refresh_and_deletion(container, monkeypatch):
    midnight = datetime(2026, 11, 8).astimezone(timezone.utc)
    now = midnight - timedelta(minutes=1)
    monkeypatch.setattr(repositories, '_utc_now', lambda: now)
    account_id = container.accounts.list()[0].id
    another = container.accounts.add(email='other@example.invalid', key='fake', url='https://example.invalid')

    def complete_with(account_id):
        task = container.tasks.create(dataset_id='test', request_payload={})[0]
        repo = container.tasks_repository
        assert repo.claim_next('test-worker', account_id=account_id).id == task.id
        repo.record_submission(task.id, task.id, 1)
        return repo.apply_remote(task.id, 'successful', ASSETS, 1, remote_id=task.id)

    earlier = complete_with(account_id)
    # 移除新标记，模拟升级前已保存的首次完成事件。
    with container.database.session(immediate=True) as session:
        session.execute(update(TaskEventRow).where(TaskEventRow.task_id == earlier.id)
                        .values(payload=func.json_remove(TaskEventRow.payload, '$.used_account_id')))
    assert container.accounts.list()[0].today_used_count == 1

    now = midnight
    container.tasks.refresh(earlier.id)
    container.tasks_repository.apply_remote(earlier.id, 'successful', ASSETS, 1, remote_id=earlier.id)
    assert container.accounts.list()[0].today_used_count == 0

    complete_with(account_id)
    today = complete_with(another.id)
    container.tasks.delete(today.id)
    with TestClient(create_app(container, with_worker=False)) as client:
        accounts = {item['id']: item for item in client.get('/api/v1/accounts').json()['items']}
        assert accounts[account_id]['today_used_count'] == 1
        assert accounts[account_id]['used_count'] == 2
        assert accounts[another.id]['today_used_count'] == 1
        assert accounts[another.id]['last_used'] is not None


def test_empty_result_not_ready_and_bound_account_never_rotates(container, monkeypatch):
    task = submitted(container, monkeypatch)
    with pytest.raises(ValueError):
        container.tasks_repository.apply_remote(task.id,'successful',[],1,remote_id='remote-1')
    original = container.tasks.get(task.id).account_id
    container.accounts.add(email='another@example.invalid',key='other',url='https://other.invalid')
    container.accounts.delete(original)
    claim(container)
    monkeypatch.setattr(CDSProvider,'inspect',lambda *args:pytest.fail('切换到其他账号'))
    RequestEngine(container).execute(task.id)
    current = container.tasks.get(task.id)
    assert current.account_id==original and current.error_message

def test_api_rejects_local_download_options_and_exposes_request_settings(container):
    with TestClient(create_app(container, with_worker=False)) as client:
        for option in ['output_dir','filename','overwrite','enqueue']:
            assert client.post('/api/v1/tasks',json={'dataset_id':'test','request_payload':{},option:True}).status_code==422
        assert client.get('/api/v1/directories').status_code==404
        settings = client.get('/api/v1/settings').json()
        assert 'requests' in settings and 'download' not in settings
        assert client.patch('/api/v1/settings',json={'values':{'requests':{'max_workers':0}}}).status_code==422
        assert container.settings.requests.max_workers==4

def test_cli_no_download_flags_and_outputs_links(container, monkeypatch):
    runner = CliRunner()
    options = ['--config-dir',str(container.settings.config_dir),'--database',str(container.settings.database_path)]
    for command in [['task','create'],['request','preview']]:
        help = runner.invoke(app,[*options,*command,'--help'])
        assert help.exit_code==0
        assert '--output-dir' not in help.output and '--overwrite' not in help.output
    task = submitted(container,monkeypatch)
    claim(container)
    container.tasks_repository.apply_remote(task.id,'successful',ASSETS,1,remote_id='remote-1')
    result = runner.invoke(app,[*options,'task','links',task.id])
    assert result.exit_code==0 and URL in result.output
    assert 'private-key' not in result.output

@pytest.mark.parametrize("values", [
    {"max_workers":0}, {"max_workers":True}, {"poll_interval":0}, {"poll_interval":True},
    {"retry_delays":[]}, {"retry_delays":[-1]}, {"retry_delays":[float("nan")]},
])
def test_invalid_request_settings_are_rejected_before_persistence(container,values):
    with pytest.raises(ValueError):
        container.update_settings({"requests":values})
    assert container.settings.requests.max_workers==4
    path=container.settings.config_dir/"app.yaml"
    assert not path.exists()

def test_rejected_submission_counts_once_but_query_errors_do_not(container,monkeypatch):
    from ecmwf_downloader.infrastructure.cds import SubmissionRejected
    def rejected(*args): raise SubmissionRejected("请求被拒绝")
    monkeypatch.setattr(CDSProvider,"submit",rejected)
    task=container.tasks.create(dataset_id="test",request_payload={})[0]
    claim(container)
    RequestEngine(container).execute(task.id)
    assert container.accounts.list()[0].fail_count==1
    assert container.tasks.get(task.id).remote_status=="rejected"
    container.tasks_repository.submission_failed(task.id,"请求被拒绝",uncertain=False,rejected=True)
    assert container.accounts.list()[0].fail_count==1

def test_monitor_failure_must_not_orphan_remote_job_when_deleting(container,monkeypatch):
    task=submitted(container,monkeypatch)
    container.tasks_repository.query_failed(task.id,"网络失败")
    container.tasks_repository.query_failed(task.id,"网络失败")
    assert container.accounts.list()[0].fail_count==0
    with pytest.raises(ValueError,match="仍可能运行"):
        container.tasks.delete(task.id)
    assert container.tasks.cancel(task.id).status==TaskStatus.CANCELLING

def test_post_ack_database_retry_never_posts_a_second_request(container,monkeypatch):
    calls=[]
    monkeypatch.setattr(CDSProvider,"submit",lambda *args:(calls.append(1) or "known-after-ack"))
    original=container.tasks_repository.record_submission
    writes=[]
    def persist(*args):
        writes.append(1)
        if len(writes)==1:
            raise RuntimeError("模拟首次持久化失败")
        return original(*args)
    monkeypatch.setattr(container.tasks_repository,"record_submission",persist)
    task=container.tasks.create(dataset_id="test",request_payload={})[0]
    claim(container)
    RequestEngine(container).execute(task.id)
    assert len(calls)==1 and len(writes)==2
    assert container.tasks.get(task.id).remote_request_id=="known-after-ack"
