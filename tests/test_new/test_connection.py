import json
import logging
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import RequestEngine
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider
from ecmwf_downloader.interfaces.http.app import create_app


@pytest.mark.parametrize('status, phrase', [(401, 'API Key'), (403, 'API Key'), (404, 'API 地址'), (500, 'HTTP 500')])
def test_authentication_errors_explain_cause_without_leaking_key(monkeypatch, status, phrase):
    import ecmwf_downloader.infrastructure.cds as module
    response = requests.Response()
    response.status_code = status
    def bad_client(**kwargs):
        raise requests.HTTPError('private-token=do-not-expose', response=response)
    monkeypatch.setattr(module, 'DatastoresClient', bad_client)
    ok, message = CDSProvider({'key': 'do-not-expose'}).check_connection()
    assert ok is False and phrase in message
    assert 'do-not-expose' not in message


@pytest.mark.parametrize('error, phrase', [
    (requests.Timeout, '超时'),
    (requests.exceptions.SSLError, '证书'),
    (requests.ConnectionError, '网络'),
    (RuntimeError, '客户端配置'),
])
def test_transport_errors_are_safe_and_distinguishable(monkeypatch, error, phrase):
    import ecmwf_downloader.infrastructure.cds as module
    def bad_client(**kwargs):
        raise error('private-token=do-not-expose')
    monkeypatch.setattr(module, 'DatastoresClient', bad_client)
    ok, message = CDSProvider({'key': 'do-not-expose'}).check_connection()
    assert ok is False and phrase in message
    assert 'do-not-expose' not in message


def test_connection_uses_official_authentication_without_downloading(monkeypatch):
    import ecmwf_downloader.infrastructure.cds as module
    calls = []
    class Client:
        def __init__(self, **kwargs):
            assert kwargs['url'] == 'https://example.invalid/api'
            assert kwargs['maximum_tries'] == 1
            assert kwargs['timeout'] == (10, 20)
        def check_authentication(self):
            calls.append('authentication')
            return {'status': 'verified'}
    monkeypatch.setattr(module, 'DatastoresClient', Client)
    ok, message = CDSProvider({'key': 'fake-key', 'url': 'https://example.invalid/api/'}).check_connection()
    assert ok and '认证通过' in message
    assert calls == ['authentication']


@pytest.mark.parametrize('ok', [True, False])
def test_manual_connection_checks_never_modify_download_counters(tmp_path: Path, monkeypatch, ok):
    container = AppContainer(AppSettings(database_path=tmp_path/'db.sqlite3', config_dir=tmp_path/'config'))
    account = container.accounts.add(email='fake@example.invalid', key='fake-key', url='https://example.invalid/api')
    container.accounts.record_failure(account.id, 'previous download failure')
    before = container.accounts.list()[0].model_dump()
    monkeypatch.setattr(CDSProvider, 'check_connection', lambda self: (ok, 'safe explanation'))
    with TestClient(create_app(container, with_worker=False)) as client:
        for _ in range(6):
            response = client.post(f'/api/v1/accounts/{account.id}/test')
            assert response.json() == {'ok': ok, 'message': 'safe explanation'}
            assert 'fake-key' not in response.text
        assert client.get('/api/v1/accounts').json()['items'][0] == before
    container.database.engine.dispose()



def test_cds_client_errors_do_not_leak_to_api_tasks_account_errors_or_events(tmp_path, monkeypatch, caplog):
    import ecmwf.datastores
    import ecmwf_downloader.infrastructure.cds as module

    key = "synthetic-cds-key"
    token = "synthetic-upstream-token"
    raw = f"Authorization: Bearer {key}; https://example.invalid/result?token={token}"

    class FailingClient:
        def __init__(self, **kwargs):
            assert kwargs["key"] == key
            kwargs["log_callback"](logging.DEBUG, raw)

        def check_authentication(self):
            self.submit()

        def get_collection(self, *_):
            # 有些客户端在没有 Response 的情况下抛出 HTTPError。
            raise requests.HTTPError(raw)

        def submit(self, *_):
            response = requests.Response()
            response.status_code = 403
            raise requests.HTTPError(raw, response=response)

        def get_remote(self, *_):
            raise requests.ConnectionError(raw)

    monkeypatch.setattr(module, "DatastoresClient", FailingClient)
    monkeypatch.setattr(ecmwf.datastores, "Client", FailingClient)
    caplog.set_level(logging.DEBUG)
    container = AppContainer(AppSettings(database_path=tmp_path / "db", config_dir=tmp_path / "config"))
    account = container.accounts.add(email="fixture@example.invalid", key=key, url="https://example.invalid/api")
    repository = container.tasks_repository
    engine = RequestEngine(container)

    with TestClient(create_app(container, with_worker=False)) as client:
        invalid = client.post("/api/v1/accounts", json={"key": {key: token}})
        assert invalid.status_code == 422
        invalid_url = client.patch(f"/api/v1/accounts/{account.id}", json={"url": f"https://user:{key}@example.invalid"})
        assert invalid_url.status_code == 422
        auth = client.post(f"/api/v1/accounts/{account.id}/test")
        assert auth.json()["ok"] is False
        schema = client.get("/api/v1/datasets/test/schema")
        assert schema.json()["source"] == "error"

        submitted = container.tasks.create(dataset_id="test", request_payload={})[0]
        repository.claim_next("worker", account_id=account.id)
        engine.execute(submitted.id)
        submission = client.get(f"/api/v1/tasks/{submitted.id}")
        assert submission.json()["status"] == TaskStatus.FAILED

        polling = container.tasks.create(dataset_id="test", request_payload={})[0]
        repository.claim_next("worker", account_id=account.id)
        repository.record_submission(polling.id, "known-remote-id", 1)
        engine.execute(polling.id)
        query = client.get(f"/api/v1/tasks/{polling.id}")
        assert query.json()["error_message"]
        assert query.json()["status"] == TaskStatus.ACCEPTED

        # 旧账号错误可能含原始异常；读出时也应返回安全提示。
        container.accounts.record_failure(account.id, raw)
        accounts = client.get("/api/v1/accounts")
        assert accounts.json()["items"][0]["last_error"]
        events = json.dumps(repository.events_after(0), ensure_ascii=False)
        outputs = [invalid.text, invalid_url.text, auth.text, schema.text, submission.text,
                   query.text, accounts.text, events, caplog.text]
        assert all(key not in output and token not in output for output in outputs)
    container.database.engine.dispose()


def test_invalid_secret_yaml_never_echoes_document(tmp_path, caplog):
    container = AppContainer(AppSettings(database_path=tmp_path / "db", config_dir=tmp_path / "config"))
    container.secrets.path.write_text("accounts: [synthetic-key\n", encoding="utf-8")
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.get("/api/v1/accounts")
        assert response.status_code == 503
        assert "synthetic-key" not in response.text + caplog.text
    container.database.engine.dispose()
