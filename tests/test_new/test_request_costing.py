from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.datasets import DatasetService
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.schema import finish_schema
from ecmwf_downloader.infrastructure.datastores import DatastoresProvider
from ecmwf_downloader.infrastructure.mirrors import NCAR_ID
from ecmwf_downloader.interfaces.http.app import create_app


ACCOUNT = {'url': 'https://cds.climate.copernicus.eu/api', 'key': 'test-only-secret'}


def provider_result(monkeypatch, result):
    calls = []
    monkeypatch.setattr(DatastoresProvider, '__init__', lambda self, **kwargs: None)
    def estimate(self, dataset_id, selection):
        calls.append((dataset_id, selection))
        return result
    monkeypatch.setattr(DatastoresProvider, 'estimate_costs', estimate)
    return calls


def test_provider_uses_official_sdk_costing():
    calls = []
    provider = object.__new__(DatastoresProvider)
    provider.client = SimpleNamespace(estimate_costs=lambda *args: calls.append(args) or {'id': 'size', 'cost': 6, 'limit': 121000})
    assert provider.estimate_costs('era5', {'variable': ['2m_temperature']})['cost'] == 6
    assert calls == [('era5', {'variable': ['2m_temperature']})]


@pytest.mark.parametrize('cost,limit', [(6, 121000), (0, 10), (100, 10), (2, 0), (2, None)])
def test_costing_preserves_official_units_and_limits(monkeypatch, cost, limit):
    calls = provider_result(monkeypatch, {'id': 'size', 'cost': cost, 'limit': limit})
    result = DatasetService().costing('era5', {'variable': ['t']}, ACCOUNT)
    assert result == {'source': 'online', 'error': None, 'id': 'size', 'cost': cost, 'limit': limit}
    assert calls == [('era5', {'variable': ['t']})]
    assert not {'bytes', 'megabytes', 'gigabytes'} & result.keys()


@pytest.mark.parametrize('result', [{}, {'cost': True}, {'cost': -1}, {'cost': float('inf')}, {'cost': 1, 'limit': 'bad'}])
def test_invalid_official_costing_is_not_presented_as_zero(monkeypatch, result):
    provider_result(monkeypatch, result)
    result = DatasetService().costing('era5', {}, ACCOUNT)
    assert result['source'] == 'error' and 'cost' not in result


def test_missing_account_and_mirror_do_not_call_cds(monkeypatch):
    calls = provider_result(monkeypatch, {})
    assert DatasetService().costing('era5', {}, None)['source'] == 'error'
    assert DatasetService().costing(NCAR_ID, {}, ACCOUNT)['source'] == 'not_applicable'
    assert calls == []


def test_costing_errors_do_not_expose_credentials(monkeypatch):
    monkeypatch.setattr(DatastoresProvider, '__init__', lambda self, **kwargs: None)
    def fail(*args):
        raise RuntimeError(ACCOUNT['key'])
    monkeypatch.setattr(DatastoresProvider, 'estimate_costs', fail)
    result = DatasetService().costing('era5', {}, ACCOUNT)
    assert result['source'] == 'error'
    assert ACCOUNT['key'] not in str(result)


def test_http_costing_checks_revision_and_compiled_payload_without_creating_tasks(tmp_path, monkeypatch):
    container = AppContainer(AppSettings(database_path=tmp_path/'db', config_dir=tmp_path/'config'))
    schema = finish_schema({'collection_id': 'test', 'fields': [DatastoresProvider._field('month', {'type': 'StringListArrayWidget', 'required': True, 'details': {'values': ['01', '02']}})]})
    container.datasets._cache[('test', None)] = (0, schema)
    monkeypatch.setattr(container.accounts, 'next_available', lambda: ACCOUNT)
    calls = provider_result(monkeypatch, {'id': 'size', 'cost': 6, 'limit': 121000})
    body = {'request_payload': {'month': ['01']}, 'schema_revision': schema['revision'], 'editor_values': {'month': ['01']}}
    try:
        with TestClient(create_app(container, with_worker=False)) as client:
            result = client.post('/api/v1/datasets/test/costing', json=body)
            assert result.status_code == 200 and result.json()['cost'] == 6
            assert calls == [('test', {'month': ['01']})]
            for invalid in [dict(body, request_payload={'month': ['02']}), dict(body, schema_revision='old'), dict(body, editor_values={'month': ['99']}), {'editor_values': {}}]:
                assert client.post('/api/v1/datasets/test/costing', json=invalid).status_code == 422
            assert len(calls) == 1 and container.tasks.list()[1] == 0
    finally:
        container.database.engine.dispose()


def test_smart_split_costs_the_previewed_children_and_returns_largest_with_its_limit(tmp_path, monkeypatch):
    container = AppContainer(AppSettings(database_path=tmp_path/'db', config_dir=tmp_path/'config'))
    values = {'year': ['2024'], 'month': ['01'], 'day': [f'{day:02}' for day in range(1, 11)]}
    schema = finish_schema({'collection_id': 'test', 'fields': [
        DatastoresProvider._field(name, {'type': 'StringListArrayWidget', 'required': True, 'details': {'values': options}})
        for name, options in values.items()
    ]})
    assert 'smart' in schema['capabilities']['split_strategies']
    container.datasets._cache[('test', None)] = (0, schema)
    monkeypatch.setattr(container.accounts, 'next_available', lambda: ACCOUNT)
    calls = []
    failing = False
    monkeypatch.setattr(DatastoresProvider, '__init__', lambda self, **kwargs: None)

    def estimate(self, dataset_id, selection):
        calls.append(selection)
        start = selection['day'][0]
        if failing and start == '08':
            raise RuntimeError(ACCOUNT['key'])
        cost, limit = {'01': (40, 100), '05': (30, 20), '08': (30, 60)}[start]
        return {'cost': cost, 'limit': limit}

    monkeypatch.setattr(DatastoresProvider, 'estimate_costs', estimate)
    body = {'request_payload': values, 'editor_values': values, 'schema_revision': schema['revision'],
            'split_strategy': 'smart', 'split_count': 3}
    try:
        with TestClient(create_app(container, with_worker=False)) as client:
            preview = client.post('/api/v1/requests/preview', json={**body, 'dataset_id': 'test'})
            assert preview.status_code == 200
            planned = [item['request_payload'] for item in preview.json()['items']]
            costing = client.post('/api/v1/datasets/test/costing', json=body).json()
            assert costing == {'source': 'online', 'error': None, 'id': None, 'cost': 40, 'limit': 100,
                               'request_count': 3, 'estimated_count': 3, 'over_limit_count': 1, 'max_index': 1}
            assert sorted(calls, key=lambda item: item['day'][0]) == planned
            assert container.tasks.list()[1] == 0
            failing = True
            incomplete = client.post('/api/v1/datasets/test/costing', json=body).json()
            assert incomplete['source'] == 'error' and incomplete['estimated_count'] == 2
            assert 'cost' not in incomplete and 'limit' not in incomplete and ACCOUNT['key'] not in str(incomplete)
            invalid = client.post('/api/v1/tasks', json={**body, 'dataset_id': 'test', 'split_count': 11})
            assert invalid.status_code == 422 and container.tasks.list()[1] == 0
            created = client.post('/api/v1/tasks', json={**body, 'dataset_id': 'test'})
            assert created.status_code == 200
            assert [item['request_payload'] for item in created.json()['items']] == planned
    finally:
        container.database.engine.dispose()
