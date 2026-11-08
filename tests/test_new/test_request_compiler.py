"""验证官方控件编码、分组语义和预览/创建闭环。"""
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.request_compiler import compile_request
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.schema import finish_schema
from ecmwf_downloader.infrastructure.datastores import DatastoresProvider
from ecmwf_downloader.interfaces.http.app import create_app


def document(form):
    return finish_schema({'collection_id': 'test-timeseries', 'title': 'Test', 'fields': DatastoresProvider._fields(SimpleNamespace(form=form))})


def timeseries():
    return document([
        {'name': 'variable', 'type': 'StringListWidget', 'required': True, 'details': {'values': ['temperature', 'wind']}},
        {'name': 'date', 'type': 'DateRangeWidget', 'required': True, 'details': {'minStart': '2024-01-01', 'maxEnd': '2024-12-31', 'defaultStart': '2024-01-01', 'defaultEnd': '2024-12-31'}},
        {'name': 'geo', 'type': 'ExclusiveGroupAccordionWidget', 'children': ['location', 'area'], 'details': {'default': 'location', 'titles': {'location': 'Point', 'area': 'Area'}}},
        {'name': 'location', 'type': 'GeographicLocationWidget', 'details': {'range': {'n': 60, 's': 20, 'w': -30, 'e': 50}}},
        {'name': 'area', 'type': 'GeographicExtentWidget', 'details': {'range': {'n': 60, 's': 20, 'w': -30, 'e': 50}, 'maximum_extent': {'lat': 2, 'lon': 2}, 'minimum_extent': {'lat': .25, 'lon': .25}}},
    ])


def values():
    return {'variable': ['temperature'], 'date': ['2024-02-28', '2024-02-29'], 'geo': 'location', 'location': [31, 20], 'area': [32, 20, 31, 21]}


def test_official_dates_and_location_encoding_and_branch_pruning():
    schema = timeseries()
    assert schema['support_status'] == 'full'
    assert schema['roots'] == ['variable', 'date', 'geo']
    result = compile_request(schema, values()).checked()
    assert result == {'variable': ['temperature'], 'date': ['2024-02-28/2024-02-29'], 'location': {'latitude': 31, 'longitude': 20}}
    area = compile_request(schema, {**values(), 'geo': 'area'}).checked()
    assert 'location' not in area and area['area'] == [32, 20, 31, 21]
    assert compile_request(schema, result, wire=True).checked() == result
    assert schema['capabilities']['split_strategies'] == ['none']


@pytest.mark.parametrize('change', [
    {'date': ['2024-02-30', '2024-03-01']}, {'date': ['2024-03-02', '2024-03-01']},
    {'date': ['2023-12-31', '2024-01-01']}, {'location': [None, 20]}, {'location': [70, 20]},
    {'geo': 'area', 'area': [40, 20, 30, 21]}, {'geo': 'area', 'area': [32, 20, 31.9, 21]},
    {'geo': 'other'}, {'variable': [True]}, {'extra': 'unknown'},
])
def test_invalid_active_inputs_cannot_be_compiled(change):
    result = compile_request(timeseries(), {**values(), **change})
    assert result.errors
    with pytest.raises(ValueError):
        result.checked()


def test_whole_range_defaults_and_help_are_not_parameters():
    schema = document([
        {'name': 'geo', 'type': 'ExclusiveGroupWidget', 'children': ['global', 'area'], 'details': {'default': 'global'}},
        {'name': 'global', 'type': 'FreeEditionWidget', 'details': {'text': 'Whole coverage'}},
        {'name': 'area', 'type': 'GeographicExtentWidget'},
        {'name': 'levels_help', 'type': 'FreeEditionWidget', 'details': {'text': 'hPa depends on level type'}},
    ])
    assert compile_request(schema, {'geo': 'global', 'area': [90, -180, -90, 180]}).checked() == {}
    assert next(field for field in schema['fields'] if field['name'] == 'levels_help')['description'] == 'hPa depends on level type'


def test_unknown_optional_paths_and_invalid_structure_are_explicit():
    schema = document([{'name': 'known', 'type': 'StringWidget'}, {'name': 'future', 'type': 'FutureWidget'}])
    assert schema['support_status'] == 'partial'
    assert compile_request(schema, {'known': 'ok'}).checked() == {'known': 'ok'}
    assert compile_request(schema, {'future': 'x'}).errors
    broken = document([{'name': 'group', 'type': 'ExclusiveGroupWidget', 'children': ['missing']}])
    assert broken['support_status'] == 'unavailable' and compile_request(broken, {}).errors
    cycle = document([{'name': 'group', 'type': 'ExclusiveGroupWidget', 'children': ['group']}])
    assert any(item['code'] == 'cyclic_group' for item in cycle['diagnostics'])


def test_scalar_selection_array_wire_type_and_typed_values():
    schema = document({'properties': {
        'month': {'type': 'array', 'items': {'type': 'string', 'enum': ['01', '02']}},
        'flag': {'type': 'boolean'}, 'count': {'type': 'integer', 'minimum': 0},
    }, 'required': ['month']})
    field = schema['fields'][0]
    field['field_type'] = 'choice'
    result = compile_request(schema, {'month': '01', 'flag': False, 'count': 0}).checked()
    assert result == {'month': ['01'], 'flag': False, 'count': 0}
    assert compile_request(schema, {'month': 1}).errors


def test_object_and_array_constraints():
    schema = document({'properties': {'config': {'type': 'object', 'properties': {'count': {'type': 'integer'}}, 'required': ['count']}, 'levels': {'type': 'array', 'minItems': 2, 'items': {'type': 'number'}}}})
    assert not compile_request(schema, {'config': {'count': 2}, 'levels': [1, 2]}).errors
    assert compile_request(schema, {'config': {}, 'levels': [1]}).errors


def test_http_preview_and_create_share_compiler_and_reject_old_revision(tmp_path, monkeypatch):
    c = AppContainer(AppSettings(database_path=tmp_path/'db', config_dir=tmp_path/'config'))
    schema = timeseries()
    c.datasets._cache[('test', None)] = (0, schema)
    try:
        with TestClient(create_app(c, with_worker=False)) as client:
            body = {'dataset_id': schema['collection_id'], 'request_payload': compile_request(schema, values()).checked(), 'editor_values': values(), 'schema_revision': schema['revision']}
            preview = client.post('/api/v1/requests/preview', json=body)
            assert preview.status_code == 200
            created = client.post('/api/v1/tasks', json=body)
            assert created.status_code == 200
            task = created.json()['items'][0]
            assert task['request_payload'] == preview.json()['items'][0]['request_payload']
            assert task['status'] == 'queued' and 'output_path' not in task
            invalid = {**body, 'editor_values': {**values(), 'location': [None, 20]}}
            assert client.post('/api/v1/tasks', json=invalid).status_code == 422
            assert client.post('/api/v1/tasks', json={**body, 'request_payload': {}}).status_code == 422
            assert client.post('/api/v1/tasks', json={**body, 'schema_revision': None}).status_code == 422
            c.datasets._cache.clear()
            assert client.post('/api/v1/tasks', json=body).status_code == 422
            assert c.tasks.list()[1] == 1
    finally:
        c.database.engine.dispose()


def test_decimal_extent_and_required_nested_json_object():
    schema = document([{'name': 'area', 'type': 'GeographicExtentWidget', 'details': {'minimum_extent': {'lat': .1, 'lon': .1}}}])
    assert not compile_request(schema, {'area': [50.3, 20.2, 50.2, 20.3]}).errors
    nested = document({'properties': {'config': {'type': 'object', 'properties': {'inner': {'type': 'object', 'properties': {'count': {'type': 'integer'}}, 'required': ['count']}}, 'required': ['inner']}}, 'required': ['config']})
    assert compile_request(nested, {'config': {'inner': {'count': 0}}}).checked() == {'config': {'inner': {'count': 0}}}
    assert compile_request(nested, {'config': {'inner': {}}}).errors


def test_cli_compile_and_checked_preview_use_same_contract(tmp_path, monkeypatch):
    import json
    from typer.testing import CliRunner
    from ecmwf_downloader.application.datasets import DatasetService
    from ecmwf_downloader.interfaces.cli.app import app
    def load(self, dataset_id, *args, **kwargs):
        schema = timeseries()
        self._cache[('fixture', None)] = (0, schema)
        return {**schema, 'source': 'online'}
    monkeypatch.setattr(DatasetService, 'schema', load)
    runner = CliRunner()
    options = ['--config-dir', str(tmp_path/'config'), '--database', str(tmp_path/'db')]
    values_args = ['--dataset','test-timeseries','--set','variable=[temperature]','--set','date=[2024-02-28,2024-02-29]','--set','geo=location','--set','location=[31,20]']
    # YAML 的日期需要显式字符串，避免把日期对象当作 API 文本。
    values_args[5] = 'date=["2024-02-28","2024-02-29"]'
    result = runner.invoke(app, [*options, 'request', 'compile', *values_args])
    assert result.exit_code == 0, result.output
    compiled = json.loads(result.stdout)['request_payload']
    assert compiled['location'] == {'latitude':31,'longitude':20}
    wire_args = ['--dataset','test-timeseries','--schema-check','--set','variable=[temperature]','--set','date=["2024-02-28/2024-02-29"]','--set','location={latitude: 31, longitude: 20}']
    result = runner.invoke(app, [*options, 'request', 'preview', *wire_args])
    assert result.exit_code == 0, result.output
    assert json.loads(result.stdout)[0]['request_payload'] == compiled


def test_incomplete_wire_coordinates_and_nested_unsupported_are_reported():
    wire = compile_request(timeseries(), values()).checked()
    assert compile_request(timeseries(), {**wire, 'location': {'latitude':31}}, wire=True).errors
    schema = document({'properties': {'config': {'type':'object','properties': {'future':{'oneOf':[{'type':'string'},{'type':'integer'}]}}}}})
    assert schema['support_status'] == 'partial'
    assert schema['diagnostics'][0]['field'] == 'config.future'
