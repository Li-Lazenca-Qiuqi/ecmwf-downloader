import sqlite3
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import pytest
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.db import TaskRow
from ecmwf_downloader.infrastructure.repositories import LeaseRepository

@pytest.fixture
def container(tmp_path):
    c = AppContainer(AppSettings(database_path=tmp_path/'db',config_dir=tmp_path/'config'))
    yield c
    c.database.engine.dispose()

def test_task_transitions_write_events_and_illegal_completion_rejected(container):
    task = container.tasks.create(dataset_id='test',request_payload={})[0]
    result = container.tasks.cancel(task.id)
    assert result.status==TaskStatus.CANCELLED
    assert [e['event_type'] for e in container.tasks_repository.events_after()]==['task.created','task.status_changed']
    assert container.tasks_repository.apply_remote(task.id,'successful',[{'url':'https://files.invalid/f.nc'}],1).status==TaskStatus.CANCELLED

def test_secrets_are_masked_from_account_listing(container):
    container.accounts.add(email='test@example.invalid',key='secret',url='https://example.invalid')
    assert all('key' not in account.model_dump() for account in container.accounts.list())
    assert (container.settings.config_dir/'secrets.yaml').stat().st_mode&0o777==0o600

def test_stale_submit_becomes_unknown_and_known_id_resumes(container):
    repo=container.tasks_repository
    unknown=container.tasks.create(dataset_id='test',request_payload={})[0]
    repo.claim_next('old-worker',account_id='original')
    assert repo.recover_stale()==[] and repo.get(unknown.id).status==TaskStatus.SUBMITTING
    with container.database.session(immediate=True) as session:
        session.get(TaskRow,unknown.id).lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert repo.recover_stale()==[unknown.id]
    assert repo.get(unknown.id).status==TaskStatus.SUBMISSION_UNKNOWN
    assert repo.claim_next('new-worker',account_id='another') is None
    repo.attach_remote(unknown.id,'remote-1')
    repo.claim_next('old-poller')
    with container.database.session(immediate=True) as session:
        session.get(TaskRow,unknown.id).lease_expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    repo.recover_stale()
    resumed=repo.claim_next('new-poller')
    assert resumed.remote_request_id=='remote-1' and resumed.account_id=='original'

def test_scheduler_lease_serializes_multiple_contenders(container):
    leases=LeaseRepository(container.database)
    with ThreadPoolExecutor(max_workers=4) as pool:
        result=list(pool.map(lambda i:leases.acquire('scheduler',str(i)),range(8)))
    assert sum(result)==1
    owner=str(result.index(True))
    leases.release('scheduler','wrong-owner')
    assert not leases.acquire('scheduler','other')
    leases.release('scheduler',owner)
    assert leases.acquire('scheduler','other')

def test_new_request_tables_preserve_legacy_database_and_user_files(tmp_path):
    db=tmp_path/'db'
    with sqlite3.connect(db) as conn:
        conn.execute('CREATE TABLE tasks (id TEXT PRIMARY KEY, output_path TEXT)')
        conn.execute('INSERT INTO tasks VALUES (?,?)',('old','existing.nc'))
        conn.execute('CREATE TABLE task_events (id INTEGER PRIMARY KEY, payload TEXT)')
        conn.execute('INSERT INTO task_events VALUES (1,?)',('old-event',))
    data=tmp_path/'existing.nc'
    data.write_bytes(b'user-file')
    c=AppContainer(AppSettings(database_path=db,config_dir=tmp_path/'config'))
    try:
        c.tasks.create(dataset_id='test',request_payload={})
        with sqlite3.connect(db) as conn:
            assert conn.execute('SELECT * FROM tasks').fetchall()==[('old','existing.nc')]
            assert conn.execute('SELECT payload FROM task_events').fetchone()[0]=='old-event'
        assert data.read_bytes()==b'user-file'
    finally: c.database.engine.dispose()

def test_request_claim_only_one_worker(container):
    task=container.tasks.create(dataset_id='test',request_payload={})[0]
    with ThreadPoolExecutor(max_workers=2) as pool:
        result=list(pool.map(lambda worker:container.tasks_repository.claim_next(worker,account_id='one'),['a','b']))
    assert sum(item is not None for item in result)==1
    assert next(item for item in result if item).id==task.id

def test_old_scheduler_cannot_claim_after_lease_transferred(container):
    from ecmwf_downloader.infrastructure.db import SchedulerLeaseRow
    task=container.tasks.create(dataset_id="test",request_payload={})[0]
    assert container.lease_repository.acquire("fenced-scheduler","old-owner")
    with container.database.session(immediate=True) as session:
        session.get(SchedulerLeaseRow,"fenced-scheduler").expires_at=datetime.now(timezone.utc)-timedelta(seconds=1)
    assert container.lease_repository.acquire("fenced-scheduler","new-owner")
    assert container.tasks_repository.claim_next("old-owner",account_id="one",lease_name="fenced-scheduler") is None
    assert container.tasks_repository.claim_next("new-owner",account_id="one",lease_name="fenced-scheduler").id==task.id
