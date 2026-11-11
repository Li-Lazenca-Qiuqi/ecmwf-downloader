import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ecmwf_downloader.application import datasets
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.infrastructure import catalogue
from ecmwf_downloader.interfaces.cli.app import app
from ecmwf_downloader.interfaces.http.app import create_app


def mock_pages(monkeypatch, pages):
    calls = []
    class Session:
        def __enter__(self): return self
        def __exit__(self, *args): pass
        def get(self, url, **kwargs):
            calls.append(url)
            page = pages[len(calls) - 1]
            if isinstance(page, Exception): raise page
            return SimpleNamespace(raise_for_status=lambda: None, json=lambda: page)
    monkeypatch.setattr(catalogue.requests, 'Session', Session)
    return calls


def test_complete_catalogue_follows_pages_deduplicates_and_preserves_titles(monkeypatch):
    calls = mock_pages(monkeypatch, [
        {'collections': [{'id':'z', 'title':'Zonal wind'}], 'links':[{'rel':'next','href':'?cursor=2'}]},
        {'collections': [{'id':'a', 'title':'Air temperature'}, {'id':'z','title':'Zonal wind'}]},
    ])
    assert [item['id'] for item in catalogue.fetch_catalogue()] == ['a','z']
    assert len(calls) == 2 and calls[1].endswith('?cursor=2')


@pytest.mark.parametrize('href', ['https://untrusted.invalid/data', '?limit=100'])
def test_catalogue_rejects_foreign_and_cyclic_pagination(monkeypatch, href):
    calls = mock_pages(monkeypatch, [{'collections':[{'id':'a','title':'Air'}], 'links':[{'rel':'next','href':href}]}])
    with pytest.raises(ValueError): catalogue.fetch_catalogue()
    assert len(calls) == 1


def test_incomplete_catalogue_is_not_returned_as_complete(monkeypatch):
    mock_pages(monkeypatch, [
        {'collections':[{'id':'a','title':'Air'}], 'links':[{'rel':'next','href':'?cursor=2'}]},
        RuntimeError('private error detail'),
    ])
    with pytest.raises(RuntimeError): catalogue.fetch_catalogue()


def test_cache_search_by_name_and_id_and_safe_stale_fallback(monkeypatch):
    calls = []
    def fetch(_proxy_url):
        calls.append(1)
        return [{'id':'reanalysis-demo', 'title':'Air Temperature', 'source':'CDS'}, {'id':'other','title':'Rain','source':'CDS'}]
    monkeypatch.setattr(datasets, 'fetch_catalogue', fetch)
    service = datasets.DatasetService()
    assert service.list()['source'] == 'online'
    result = service.list('AIR temperature')
    assert result['total'] == 1 and result['catalogue_total'] == 2
    result['items'].clear()
    assert service.list('REANALYSIS-DEMO')['total'] == 1
    assert len(calls) == 1
    def fail(_proxy_url): raise RuntimeError('private error detail')
    monkeypatch.setattr(datasets, 'fetch_catalogue', fail)
    stale = service.list(refresh=True)
    assert stale['source'] == 'cache' and stale['stale'] and stale['total'] == 2
    empty = datasets.DatasetService().list()
    assert empty['source'] == 'error' and empty['items'] == []
    assert 'private error detail' not in json.dumps([stale, empty])


def test_http_and_cli_expose_catalogue_search_without_credentials(tmp_path, monkeypatch):
    monkeypatch.setattr(datasets, 'fetch_catalogue', lambda _proxy_url: [{'id':'online-only-id', 'title':'Official Catalogue Entry', 'source':'CDS'}])
    settings = AppSettings(database_path=tmp_path/'db.sqlite3', config_dir=tmp_path/'config')
    container = AppContainer(settings)
    try:
        with TestClient(create_app(container, with_worker=False)) as client:
            result = client.get('/api/v1/datasets?q=CATALOGUE&refresh=true').json()
            assert result['total'] == 1 and result['items'][0]['id'] == 'online-only-id'
            assert client.get('/api/v1/datasets?q=missing').json()['items'] == []
        result = CliRunner().invoke(app, ['--config-dir',str(tmp_path/'config'),'--database',str(tmp_path/'cli.sqlite3'),'dataset','list','--search','official','--json'])
        assert result.exit_code == 0, result.output
        assert json.loads(result.stdout)[0]['id'] == 'online-only-id'
    finally:
        container.database.engine.dispose()
