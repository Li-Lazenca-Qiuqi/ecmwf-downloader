import pytest
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.interfaces.http.app import create_app


@pytest.mark.parametrize('path', ['/', '/requests/new'])
def test_web_entry_requires_cache_revalidation(tmp_path, path):
    container = AppContainer(AppSettings(database_path=tmp_path/'db', config_dir=tmp_path/'config'))
    try:
        with TestClient(create_app(container, with_worker=False)) as client:
            response = client.get(path)
            assert response.status_code == 200
            assert response.headers['cache-control'] == 'no-cache'
            assert '<script type="module"' in response.text
    finally:
        container.database.engine.dispose()
