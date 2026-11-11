import json
import logging
from types import SimpleNamespace

import httpx
import pytest
import yaml
from fastapi.testclient import TestClient

from ecmwf_downloader.application.ai import AIService
from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.interfaces.http.app import create_app


@pytest.fixture
def container(tmp_path):
    settings = AppSettings(database_path=tmp_path/'db.sqlite3', config_dir=tmp_path/'config')
    settings.config_dir.mkdir()
    (settings.config_dir/'app.yaml').write_text(yaml.safe_dump(settings.model_dump(mode='json')))
    value = AppContainer(settings)
    yield value
    value.database.engine.dispose()


def field_schema():
    return {'collection_id': 'test', 'title': 'Test', 'current_selection': {'flag': False}, 'fields': [
        {'name': 'variable', 'label': 'Variable', 'request_field': True, 'field_type': 'multiple', 'options': [{'value': 'temperature', 'label': 'Temperature', 'groups': ['Popular', 'Temperature']}]},
        {'name': 'count', 'label': 'Count', 'request_field': True, 'field_type': 'number', 'integer': True, 'minimum': 1, 'maximum': 5},
        {'name': 'flag', 'label': 'Flag', 'request_field': True, 'field_type': 'boolean'},
        {'name': 'area', 'label': 'Area', 'request_field': True, 'field_type': 'area'},
        {'name': 'licence', 'label': 'Licence', 'request_field': False, 'field_type': 'info'},
    ]}


def test_ai_configuration_never_returns_key_and_blank_preserves_key(container):
    with TestClient(create_app(container, with_worker=False)) as client:
        initial = client.get('/api/v1/ai/config').json()
        assert not initial['ready'] and not initial['has_api_key']
        assert initial['json_mode'] is True
        body = {'enabled': True, 'base_url': 'https://example.invalid/v1/', 'model': 'test-model', 'api_key': 'private-test-value', 'json_mode': True}
        response = client.patch('/api/v1/ai/config', json=body)
        assert response.status_code == 200
        assert response.json()['has_api_key']
        assert response.json()['ready'] == initial['sdk_available']
        assert 'private-test-value' not in response.text
        assert 'private-test-value' not in (container.settings.config_dir/'app.yaml').read_text()
        body['api_key'] = ''
        body['model'] = ' second-model '
        assert client.patch('/api/v1/ai/config', json=body).json()['model'] == 'second-model'
        assert container.secrets.ai_config()['api_key'] == 'private-test-value'
        assert container.ai.configuration()['model'] == 'second-model'
        assert client.get('/api/v1/settings').json()['ai']['enabled']


@pytest.mark.parametrize('changes', [
    {'base_url': 'https://user:private-test-value@example.invalid/v1'},
    {'base_url': 'https://example.invalid/v1?key=private-test-value'},
    {'base_url': 'file:///tmp/invalid'},
    {'base_url': 'http://localhost:invalid/v1'},
    {'model': '   '},
    {'enabled': {'private-test-value': True}},
])
def test_invalid_ai_configuration_is_not_saved_or_reflected(container, changes):
    before = container.secrets.snapshot()
    public = (container.settings.config_dir/'app.yaml').read_text()
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch('/api/v1/ai/config', json={
            'enabled': True, 'base_url': 'https://example.invalid/v1', 'model': 'test', 'api_key': 'private-test-value', **changes,
        })
        assert response.status_code == 422
        assert 'private-test-value' not in response.text
    assert container.secrets.snapshot() == before
    assert (container.settings.config_dir/'app.yaml').read_text() == public


def test_enable_without_key_is_rejected_before_writing(container):
    public = (container.settings.config_dir/'app.yaml').read_text()
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch('/api/v1/ai/config', json={'enabled': True, 'base_url': 'https://example.invalid/v1', 'model': 'test'})
        assert response.status_code == 422
    assert (container.settings.config_dir/'app.yaml').read_text() == public


def mock_sdk(monkeypatch, handler):
    monkeypatch.delenv('WSL_DISTRO_NAME', raising=False)
    openai = pytest.importorskip('openai')
    real_client = openai.OpenAI
    def client(**kwargs):
        configured = kwargs.pop('http_client', None)
        if configured is not None:
            configured.close()
        return real_client(**kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

    monkeypatch.setattr(openai, 'OpenAI', client)


@pytest.mark.parametrize('json_mode', [True, False])
def test_connection_uses_unsaved_form_values_without_saving(container, monkeypatch, json_mode):
    container.settings.ai = {'enabled': False, 'base_url': 'https://saved.invalid/v1'}
    before_public = container.config_path.read_bytes()
    before_secrets = container.secrets.path.read_bytes()

    def handler(request):
        assert str(request.url) == 'https://draft.invalid/v1/chat/completions'
        assert request.headers['Authorization'] == 'Bearer synthetic-draft-key'
        body = json.loads(request.content)
        assert body['model'] == 'luna'
        assert body['max_completion_tokens'] == 128 and 'max_tokens' not in body
        assert body.get('response_format') == ({'type': 'json_object'} if json_mode else None)
        return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 0, 'model': 'luna',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '{"ok":true}'}}]})

    mock_sdk(monkeypatch, handler)
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.post('/api/v1/ai/test', json={
            'enabled': False, 'base_url': 'https://draft.invalid/v1/', 'model': 'luna',
            'json_mode': json_mode, 'api_key': 'synthetic-draft-key',
        })
        assert response.status_code == 200 and '连接成功' in response.json()['message']
        assert 'synthetic-draft-key' not in response.text
    assert container.config_path.read_bytes() == before_public
    assert container.secrets.path.read_bytes() == before_secrets


def test_connection_uses_saved_key_only_at_saved_address_and_sanitizes_error(container, monkeypatch, caplog):
    container.settings.ai = {'enabled': False, 'base_url': 'https://saved.invalid/v1'}
    container.secrets.update_ai({'api_key': 'synthetic-saved-key'})
    calls = []

    def handler(request):
        calls.append(request.url.host)
        assert request.headers['Authorization'] == 'Bearer synthetic-saved-key'
        return httpx.Response(404, json={'error': {'message': 'synthetic-saved-key'}})

    mock_sdk(monkeypatch, handler)
    with TestClient(create_app(container, with_worker=False)) as client:
        body = {'enabled': False, 'model': 'luna'}
        wrong_address = client.post('/api/v1/ai/test', json={**body, 'base_url': 'https://other.invalid/v1'})
        assert wrong_address.status_code == 422 and not calls
        response = client.post('/api/v1/ai/test', json={**body, 'base_url': 'https://saved.invalid/v1/'})
        assert response.status_code == 503 and '模型或接口' in response.json()['detail']
        assert calls == ['saved.invalid']
        assert 'synthetic-saved-key' not in response.text + caplog.text


@pytest.mark.parametrize(('base_url', 'model'), [
    ('https://api.openai.com/v1', 'gpt-6-luna'),
    ('https://compatible.invalid/v1', 'openai/gpt-6-luna'),
])
def test_luna_uses_supported_json_completion_parameters(container, monkeypatch, base_url, model):
    container.settings.ai = {'enabled': True, 'base_url': base_url, 'model': model}
    container.secrets.update_ai({'api_key': 'synthetic-luna-key'})
    limits = []

    def handler(request):
        body = json.loads(request.content)
        assert str(request.url) == base_url + '/chat/completions'
        assert body['model'] == model
        assert body['response_format'] == {'type': 'json_object'}
        assert body['reasoning_effort'] == 'none'
        assert 'max_tokens' not in body and 'temperature' not in body
        limits.append(body['max_completion_tokens'])
        return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 0, 'model': 'gpt-6-luna',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '{"flag":true}'}}]})

    mock_sdk(monkeypatch, handler)
    with TestClient(create_app(container, with_worker=False)) as client:
        result = client.post('/api/v1/ai/test', json={
            'enabled': True, 'base_url': base_url, 'model': model,
        })
        assert result.status_code == 200
        suggestion = client.post('/api/v1/ai/suggestions', json={
            'field_schema': field_schema(), 'user_request': '启用 flag',
        })
        assert suggestion.json()['suggestion'] == {'flag': True}
    assert limits == [128, 4096]


@pytest.mark.parametrize('json_mode', [True, False])
def test_completion_sends_current_selection_and_validates_real_sdk_response(container, monkeypatch, json_mode):
    container.settings.ai = {'enabled': True, 'base_url': 'https://example.invalid/v1', 'model': 'test-model', 'json_mode': json_mode}
    container.secrets.update_ai({'api_key': 'private-test-value'})
    seen = []
    parameters = {'variable': ['temperature'], 'count': 3, 'flag': False, 'area': [31, 120, 30, 121]}
    def handler(request):
        body = json.loads(request.content)
        seen.append(body)
        return httpx.Response(200, json={'id': 'test', 'object': 'chat.completion', 'created': 0, 'model': 'test-model',
            'choices': [{'index': 0, 'finish_reason': 'stop', 'message': {'role': 'assistant', 'content': '```json\n'+json.dumps({'parameters': parameters})+'\n```'}}]})
    mock_sdk(monkeypatch, handler)
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.post('/api/v1/ai/suggestions', json={'field_schema': field_schema(), 'user_request': '按当前选择补全参数'})
        assert response.status_code == 200
        assert response.json()['suggestion'] == parameters
    assert len(seen) == 1
    assert seen[0]['max_completion_tokens'] == 4096 and 'max_tokens' not in seen[0]
    assert seen[0]['temperature'] == 0.3
    assert seen[0].get('response_format') == ({'type': 'json_object'} if json_mode else None)
    sent = json.loads(seen[0]['messages'][1]['content'])['field_schema']
    assert sent['current_selection'] == {'flag': False}
    assert 'licence' not in [field['name'] for field in sent['fields']]
    assert 'groups' not in sent['fields'][0]['options'][0]


def test_blank_prompt_is_rejected_before_provider_call(container):
    with pytest.raises(RuntimeError, match='填写下载需求'):
        container.ai.suggest(field_schema(), '  ')


@pytest.mark.parametrize('parameters', [
    {'unknown': 'x'}, {'variable': ['invented']}, {'variable': 'temperature'},
    {'count': True}, {'count': 8}, {'flag': 'false'}, {'area': [30, 120, 31, 121]}, {'licence': True},
])
def test_ai_partial_validation_rejects_invalid_fields_and_types(parameters):
    with pytest.raises(RuntimeError):
        AIService._validate(parameters, [field for field in field_schema()['fields'] if field['request_field']])


@pytest.mark.parametrize('status, content', [(401, {'error': {'message': 'private-test-value', 'type': 'invalid_api_key'}}), (429, {'error': {'message': 'private-test-value'}})])
def test_provider_errors_are_safe_and_not_retried(container, monkeypatch, status, content, caplog):
    caplog.set_level(logging.DEBUG)
    caplog.set_level(logging.DEBUG, logger='openai')
    container.settings.ai = {'enabled': True, 'base_url': 'https://example.invalid/v1'}
    container.secrets.update_ai({'api_key': 'private-test-value'})
    calls = []
    def handler(request):
        calls.append(1)
        return httpx.Response(status, json=content)
    mock_sdk(monkeypatch, handler)
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.post('/api/v1/ai/suggestions', json={'field_schema': field_schema(), 'user_request': '测试'})
        assert response.status_code == 503
        assert 'private-test-value' not in response.text + caplog.text
        assert len(calls) == 1


@pytest.mark.parametrize('content, finish', [('{}', 'stop'), ('[]', 'stop'), ('not-json', 'stop'), ('{"count": NaN}', 'stop'), ('{"count":', 'length')])
def test_invalid_or_incomplete_ai_output_is_rejected(container, monkeypatch, content, finish):
    container.settings.ai = {'enabled': True}
    container.secrets.update_ai({'api_key': 'private-test-value'})
    class Client:
        def __init__(self, **kwargs):
            self.chat = SimpleNamespace(completions=SimpleNamespace(create=lambda **kwargs: SimpleNamespace(choices=[SimpleNamespace(finish_reason=finish, message=SimpleNamespace(content=content))])))
        def __enter__(self): return self
        def __exit__(self, *args): pass
    openai = pytest.importorskip('openai')
    monkeypatch.setattr(openai, 'OpenAI', Client)
    with pytest.raises(RuntimeError): container.ai.suggest(field_schema(), '测试')
