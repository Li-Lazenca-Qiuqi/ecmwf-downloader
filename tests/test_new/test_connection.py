from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
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
