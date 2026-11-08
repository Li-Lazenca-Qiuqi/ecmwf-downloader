import threading
import time
from datetime import datetime, timedelta, timezone
import pytest
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import RequestScheduler
from ecmwf_downloader.config import AppSettings, RequestSettings
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider
from ecmwf_downloader.infrastructure.db import TaskRow

@pytest.fixture
def container(tmp_path):
    c=AppContainer(AppSettings(database_path=tmp_path/'db',config_dir=tmp_path/'config',
                              requests=RequestSettings(poll_interval=1)))
    c.accounts.add(email='test@example.invalid',key='secret',url='https://example.invalid')
    yield c
    c.database.engine.dispose()

def wait_until(test, timeout=4):
    end=time.monotonic()+timeout
    while time.monotonic()<end:
        if test(): return
        time.sleep(.02)
    raise AssertionError('请求状态未按预期收敛')

def test_scheduler_submits_and_polls_without_download(container,monkeypatch):
    calls=[]
    monkeypatch.setattr(CDSProvider,'submit',lambda *args:(calls.append('submit') or 'remote-1'))
    monkeypatch.setattr(CDSProvider,'inspect',lambda *args:('successful',[{'url':'https://files.invalid/f.nc'}]))
    task=container.tasks.create(dataset_id='test',request_payload={})[0]
    scheduler=RequestScheduler(container,poll_interval=.02)
    assert scheduler.start()
    try:
        wait_until(lambda:container.tasks.get(task.id).status==TaskStatus.COMPLETED)
        assert calls==['submit'] and not hasattr(CDSProvider,'download')
    finally: scheduler.stop()

def test_stop_keeps_lease_until_submission_id_is_saved(container,monkeypatch):
    entered=threading.Event(); release=threading.Event()
    def submit(*args):
        entered.set()
        assert release.wait(3)
        return 'remote-during-stop'
    monkeypatch.setattr(CDSProvider,'submit',submit)
    task=container.tasks.create(dataset_id='test',request_payload={})[0]
    scheduler=RequestScheduler(container,poll_interval=.02)
    assert scheduler.start() and entered.wait(2)
    stopped=threading.Thread(target=scheduler.stop)
    stopped.start()
    try:
        time.sleep(.05)
        assert not container.lease_repository.acquire(scheduler.LEASE_NAME,'next-owner')
    finally:
        release.set()
        stopped.join(4)
    assert not stopped.is_alive()
    assert container.tasks.get(task.id).remote_request_id=='remote-during-stop'
    assert container.lease_repository.acquire(scheduler.LEASE_NAME,'next-owner')
    container.lease_repository.release(scheduler.LEASE_NAME,'next-owner')

def test_tasks_expiring_after_start_are_recovered_without_resubmission(container,monkeypatch):
    task=container.tasks.create(dataset_id='test',request_payload={})[0]
    container.tasks_repository.claim_next('dead-worker',account_id=container.accounts.list()[0].id)
    with container.database.session(immediate=True) as session:
        session.get(TaskRow,task.id).lease_expires_at=datetime.now(timezone.utc)+timedelta(seconds=.2)
    monkeypatch.setattr(CDSProvider,'submit',lambda *args:pytest.fail('重复提交'))
    scheduler=RequestScheduler(container,poll_interval=.02)
    assert scheduler.start()
    try: wait_until(lambda:container.tasks.get(task.id).status==TaskStatus.SUBMISSION_UNKNOWN)
    finally: scheduler.stop()
