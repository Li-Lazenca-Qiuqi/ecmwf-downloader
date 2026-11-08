from pathlib import Path
from types import SimpleNamespace
import json

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.datasets import DatasetService
from ecmwf_downloader.application.request_builder import RequestBuilder
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.models import SplitStrategy
from ecmwf_downloader.infrastructure.datastores import DatastoresProvider
from ecmwf_downloader.interfaces.cli.app import app
from ecmwf_downloader.interfaces.http.app import create_app


@pytest.fixture
def container(tmp_path):
    value = AppContainer(AppSettings(database_path=tmp_path/'db.sqlite3', config_dir=tmp_path/'config'))
    yield value
    value.database.engine.dispose()


def test_complete_grouped_form_preserves_options_types_and_information():
    raw = [
        {'name': 'variable', 'label': 'Variable', 'type': 'StringListArrayWidget', 'required': True, 'details': {'groups': [
            {'label': 'Popular', 'values': ['temperature'], 'labels': {'temperature': 'Temperature'}},
            {'label': 'Other', 'values': ['temperature', 'wind', 'rain'], 'labels': {'wind': 'Wind'}},
        ]}},
        {'name': 'month', 'type': 'StringListWidget', 'details': {'values': ['01','02'], 'default': ['01','01']}},
        {'name': 'format', 'type': 'StringChoiceWidget', 'details': {'values': ['netcdf','grib'], 'default':['netcdf']}},
        {'name': 'area', 'type': 'GeographicExtentWidget', 'details': {'default': {'n': 31,'w':120,'s':30,'e':121}}},
        {'name': 'licences', 'type': 'LicenceWidget', 'details': {}, 'fields': ['name_reference']},
    ] + [{'name': f'field_{index}', 'type': 'StringWidget'} for index in range(15)]
    fields = DatastoresProvider._fields(SimpleNamespace(form=raw))
    assert len(fields) == 20
    assert fields[0]['values'] == ['temperature','wind','rain']
    assert fields[0]['options'][1] == {'value':'wind','label':'Wind','group':'Other','groups':['Other']}
    assert fields[0]['options'][0]['groups'] == ['Popular', 'Other']
    assert fields[1]['default'] == ['01']
    assert fields[2]['default'] == 'netcdf'
    assert fields[3]['default'] == [31,120,30,121]
    assert fields[4]['request_field'] is False


def test_json_schema_fields_keep_numbers_booleans_and_nested_groups():
    form = {'required':['count'], 'properties': {
        'count': {'type':'integer','minimum':-10,'default':2},
        'flag': {'type':'boolean','default':False},
        'levels': {'type':'array','items':{'type':'integer','enum':[500,700]}},
        'object': {'type':'object','default':{'nested':1}},
    }}
    fields = DatastoresProvider._fields(SimpleNamespace(form=form))
    assert fields[0]['integer'] and fields[0]['required'] and fields[0]['minimum'] == -10
    assert fields[1]['default'] is False and fields[1]['field_type'] == 'boolean'
    assert fields[2]['values'] == [500,700] and fields[2]['integer']
    assert fields[3]['field_type'] == 'unsupported'
    nested = DatastoresProvider._fields(SimpleNamespace(form=[{'name':'group','type':'GroupWidget','children':[{'name':'inner','type':'StringWidget'}]}]))
    assert any(field['name']=='inner' for field in nested)


def test_option_groups_keep_membership_without_duplicate_request_values():
    field = DatastoresProvider._field('variable', {
        'type': 'StringListArrayWidget', 'details': {
            'values': ['unclassified', 'shared'],
            'groups': [
                {'label': 'Popular', 'values': ['shared', 'shared', True, 1]},
                {'label': 'Temperature', 'values': ['shared', 1]},
            ],
        },
    })
    assert field['values'] == ['unclassified', 'shared', True, 1]
    assert field['options'][0]['groups'] == []
    assert field['options'][1]['groups'] == ['Popular', 'Temperature']
    assert field['options'][1]['group'] == 'Popular'
    assert field['options'][2]['groups'] == ['Popular']
    assert field['options'][3]['groups'] == ['Popular', 'Temperature']


def test_schema_cache_and_failure_sources_are_explicit(monkeypatch):
    monkeypatch.setattr(DatastoresProvider,'__init__',lambda self,**kwargs: None)
    service = DatasetService()
    account = {'id':'fake','key':'never-output','url':'https://example.invalid'}
    def schema(self, dataset):
        return {'collection_id':dataset,'title':dataset,'fields':[DatastoresProvider._field('actual', {'type': 'StringWidget'})]}
    monkeypatch.setattr(DatastoresProvider,'schema',schema)
    first = service.schema('test',account)
    assert first['source'] == 'online'
    first['fields'].clear()
    assert service.schema('test',account)['fields'] == [DatastoresProvider._field('actual', {'type': 'StringWidget'})]
    def fail(*args): raise RuntimeError('never-output')
    monkeypatch.setattr(DatastoresProvider,'schema',fail)
    # 阻止真实网络构造，保留应用层缓存逻辑。
    monkeypatch.setattr(DatastoresProvider,'__init__',lambda self,**kwargs: None)
    cached = service.schema('test',account,refresh=True)
    assert cached['source']=='cache' and cached['stale'] and cached['error']
    missing = service.schema('other')
    assert missing['source']=='error' and missing['fields']==[]
    assert 'never-output' not in json.dumps(cached)


@pytest.mark.parametrize('dates, expected', [
    ({'year':['2023','2024'],'month':['02'],'day':['28','29','30']},3),
    ({'year':[2024],'month':['01','02'],'day':['31']},1),
    ({'years':['2024'],'months':['02'],'days':['29','29']},1),
])
def test_day_split_filters_impossible_dates_and_preserves_payload(tmp_path, dates, expected):
    payload = {**dates,'variable':['temperature'],'area':[31,120,30,121]}
    before = json.loads(json.dumps(payload))
    warnings=[]
    plans=RequestBuilder().build(dataset_id='test',payload=payload,strategy=SplitStrategy.DAY,warnings=warnings)
    assert len(plans)==expected and len({item.label for item in plans})==expected
    assert payload==before
    assert all(item.payload['area']==[31,120,30,121] for item in plans)
    assert all(len(item.payload.get('day',item.payload.get('days')))==1 for item in plans)
    if expected>1: assert warnings


@pytest.mark.parametrize('payload, phrase', [
    ({'year':[2023],'month':[2],'day':[29]},'有效'),
    ({'year':[2024],'month':[13],'day':[1]},'month'),
    ({'year':[2024],'month':[2],'day':[0]},'day'),
    ({'year':[2024],'month':[2]},'day'),
    ({'year':[True],'month':[2],'day':[1]},'year'),
])
def test_invalid_daily_requests_fail_before_task_creation(tmp_path,payload,phrase):
    with pytest.raises(ValueError,match=phrase):
        RequestBuilder().build(dataset_id='test',payload=payload,strategy=SplitStrategy.DAY)






def test_daily_preview_matches_created_requests_and_directory_api_removed(container,tmp_path):
    request={'dataset_id':'test','request_payload':{'year':['2024'],'month':['02'],'day':['29','30']},'split_strategy':'day'}
    with TestClient(create_app(container,with_worker=False)) as client:
        preview=client.post('/api/v1/requests/preview',json=request)
        assert preview.status_code==200 and len(preview.json()['items'])==1
        assert preview.json()['warnings'] and container.tasks.list()[1]==0
        created=client.post('/api/v1/tasks',json=request).json()['items']
        assert len(created)==1 and created[0]['status']=='queued'
        assert preview.json()['items'][0]['label']==created[0]['title']
        assert preview.json()['items'][0]['request_payload']==created[0]['request_payload']
        assert client.get('/api/v1/directories').status_code == 404


def test_day_cli_preview_warns_without_writing_tasks(tmp_path):
    result=CliRunner().invoke(app,['--config-dir',str(tmp_path/'config'),'--database',str(tmp_path/'db.sqlite3'),'request','preview','--dataset','test','--set','year=[2024]','--set','month=[2]','--set','day=[29,30]','--split','day'])
    assert result.exit_code==0, result.output
    assert len(json.loads(result.stdout))==1
    assert '跳过' in result.stderr
