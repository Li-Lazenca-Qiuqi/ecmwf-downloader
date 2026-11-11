import json
from types import SimpleNamespace

import requests
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import RequestEngine
from ecmwf_downloader.config import AppSettings, NetworkProxySettings, load_settings
from ecmwf_downloader.infrastructure import cds
from ecmwf_downloader.infrastructure.catalogue import CATALOGUE_URL
from ecmwf_downloader.infrastructure import mirrors, network
from ecmwf_downloader.interfaces.http.app import create_app


PROXY = "http://proxy.invalid:32081"
AMBIENT_PROXY = "http://environment.invalid:8080"


def test_proxy_settings_probe_and_save_are_independent(tmp_path, monkeypatch):
    settings = AppSettings(database_path=tmp_path / "requests.db", config_dir=tmp_path / "config")
    container = AppContainer(settings)
    sent = []

    def send(_adapter, prepared, **kwargs):
        sent.append((prepared, kwargs))
        response = requests.Response()
        response.status_code = 200
        response._content = json.dumps({"collections": [{"id": "test", "title": "Fixture"}]}).encode()
        response.request = prepared
        return response

    monkeypatch.setenv("HTTPS_PROXY", AMBIENT_PROXY)
    monkeypatch.setenv("https_proxy", AMBIENT_PROXY)
    monkeypatch.setenv("REQUESTS_CA_BUNDLE", "/fixture/cert.pem")
    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    try:
        with TestClient(create_app(container, with_worker=False)) as client:
            assert client.get("/api/v1/settings").json()["network_proxy"] == {"mode": "system", "url": ""}
            probe = client.post("/api/v1/settings/network-proxy/test", json={"mode": "manual", "url": PROXY})
            assert probe.status_code == 200 and probe.json()["ok"]
            request, kwargs = sent.pop()
            assert request.url == CATALOGUE_URL + "?limit=1"
            assert "PRIVATE-TOKEN" not in request.headers
            assert kwargs["proxies"]["https"] == PROXY
            assert kwargs["verify"] == "/fixture/cert.pem"
            assert not container.config_path.exists()

            bad_url = "http://name:synthetic-password@proxy.invalid:32081"
            for endpoint, method, payload in (
                ("/api/v1/settings/network-proxy/test", client.post, {"mode": "manual", "url": bad_url}),
                ("/api/v1/settings", client.patch, {"values": {"network_proxy": {"mode": "manual", "url": bad_url}}}),
            ):
                response = method(endpoint, json=payload)
                assert response.status_code == 422 and "synthetic-password" not in response.text
            assert not container.config_path.exists()

            saved = client.patch("/api/v1/settings", json={"values": {"network_proxy": {"mode": "manual", "url": PROXY + "/"}}})
            assert saved.status_code == 200
            assert load_settings(settings.config_dir).network_proxy.url == PROXY
            assert client.get("/api/v1/datasets?refresh=true").json()["source"] == "online"
            assert sent.pop()[1]["proxies"]["https"] == PROXY

            disabled = client.patch("/api/v1/settings", json={"values": {"network_proxy": {"mode": "direct"}}})
            assert disabled.json()["network_proxy"] == {"mode": "direct", "url": PROXY}
            assert client.get("/api/v1/datasets?refresh=true").json()["source"] == "online"
            assert sent.pop()[1]["proxies"] == {}
            system = client.patch("/api/v1/settings", json={"values": {"network_proxy": {"mode": "system"}}})
            assert system.json()["network_proxy"]["mode"] == "system"
            assert client.get("/api/v1/datasets?refresh=true").json()["source"] == "online"
            assert sent.pop()[1]["proxies"]["https"] == AMBIENT_PROXY
    finally:
        container.database.engine.dispose()


def test_cds_operations_use_new_proxy_after_save(tmp_path, monkeypatch):
    import ecmwf.datastores

    settings = AppSettings(database_path=tmp_path / "requests.db", config_dir=tmp_path / "config")
    container = AppContainer(settings)
    seen = []

    def fake_client(*, session, **_kwargs):
        def record(operation, result):
            route = session.merge_environment_settings("https://cds.example.invalid/api", {}, None, True, None)
            seen.append((operation, route["proxies"].get("https")))
            return result

        return SimpleNamespace(
            get_collection=lambda _dataset: record("schema", SimpleNamespace(
                title="Fixture", description="",
                form=[{"name": "year", "type": "StringListArrayWidget", "details": {"values": ["2024"]}}],
            )),
            apply_constraints=lambda *_args: record("constraints", {"year": ["2024"]}),
            estimate_costs=lambda *_args: record("costing", {"cost": 1}),
            check_authentication=lambda: record("auth", None),
            submit=lambda *_args: record("submit", SimpleNamespace(request_id="job-1")),
            get_remote=lambda *_args: record("inspect", SimpleNamespace(status="accepted")),
        )

    monkeypatch.setattr(ecmwf.datastores, "Client", fake_client)
    monkeypatch.setattr(cds, "DatastoresClient", fake_client)
    try:
        account = container.accounts.add(email="example@example.invalid", key="fixture-key", url="https://cds.example.invalid/api")
        container.update_settings({"network_proxy": {"mode": "manual", "url": PROXY}})
        stored = container.accounts.next_available()
        assert container.datasets.schema("test", stored)["source"] == "online"
        assert container.datasets.constraints("test", {}, stored)["source"] == "online"
        assert container.datasets.costing("test", {}, stored)["source"] == "online"
        assert container.accounts.test(account.id)[0]

        task = container.tasks.create(dataset_id="test", request_payload={})[0]
        assert container.tasks_repository.claim_next("fixture", account_id=account.id).id == task.id
        engine = RequestEngine(container)
        engine.execute(task.id)
        engine.execute(task.id)
        assert seen == [(name, PROXY) for name in ("schema", "constraints", "costing", "auth", "submit", "inspect")]
    finally:
        container.database.engine.dispose()


def test_unified_settings_save_migrates_proxy_and_keeps_ai_key_private(tmp_path):
    config = tmp_path / "config"
    settings = AppSettings(database_path=tmp_path / "requests.db", config_dir=config)
    container = AppContainer(settings)
    try:
        container.config_path.write_text("cds_proxy:\n  enabled: true\n  url: " + PROXY + "\n")
        assert load_settings(config).network_proxy == NetworkProxySettings(mode="manual", url=PROXY)
        with TestClient(create_app(container, with_worker=False)) as client:
            response = client.patch("/api/v1/settings", json={
                "values": {"network_proxy": {"mode": "manual", "url": PROXY},
                           "requests": {"poll_interval": 11}, "ai": {"enabled": True, "model": "fixture"}},
                "ai_api_key": "synthetic-secret",
            })
            assert response.status_code == 200 and "synthetic-secret" not in response.text
            data = response.json()
            assert data["network_proxy"] == {"mode": "manual", "url": PROXY}
            assert data["requests"]["poll_interval"] == 11
            assert data["ai_config"]["enabled"] and data["ai_config"]["has_api_key"]
            assert container.secrets.ai_config()["api_key"] == "synthetic-secret"
            saved = container.config_path.read_text()
            assert "cds_proxy" not in saved and "synthetic-secret" not in saved
    finally:
        container.database.engine.dispose()


def test_wsl_system_proxy_uses_windows_only_without_environment_proxy(monkeypatch):
    monkeypatch.setenv("WSL_DISTRO_NAME", "Fixture")
    monkeypatch.setattr(network, "getproxies", lambda: {})
    monkeypatch.setattr(network, "proxy_bypass", lambda host: host == "localhost")
    monkeypatch.setattr(network, "_windows_system_proxy", lambda origin, _time: PROXY)
    settings = NetworkProxySettings()
    assert network.explicit_proxy(settings, "https://cds.example.invalid/path") == PROXY
    assert network.explicit_proxy(settings, "http://localhost/") is None
    monkeypatch.setattr(network, "getproxies", lambda: {"https": AMBIENT_PROXY})
    assert network.explicit_proxy(settings, "https://cds.example.invalid/path") is None


def test_mirror_listing_and_head_share_global_proxy(monkeypatch):
    sent = []
    key = "e5.oper.an.sfc/202401/fixture.nc"

    def send(_adapter, prepared, **kwargs):
        sent.append((prepared.method, kwargs["proxies"].get("https")))
        response = requests.Response()
        response.status_code = 200
        response.url = prepared.url
        response.request = prepared
        response.headers["Content-Length"] = "321"
        response._content = (
            f'<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">'
            f'<Contents><Key>{key}</Key><Size>321</Size></Contents></ListBucketResult>'
        ).encode() if prepared.method == "GET" else b""
        return response

    monkeypatch.setattr(requests.adapters.HTTPAdapter, "send", send)
    settings = NetworkProxySettings(mode="manual", url=PROXY)
    assert mirrors.ncar_schema(network=settings)["fields"][0]["options"][0]["value"] == key
    assert mirrors.MirrorProvider(settings).results(mirrors.NCAR_ID, {"object_key": key})[0]["size"] == 321
    assert sent == [("GET", PROXY), ("HEAD", PROXY)]


def test_ai_connection_uses_the_current_proxy_draft(tmp_path, monkeypatch):
    import pytest
    pytest.importorskip("openai")
    import httpx

    from ecmwf_downloader.application.ai import AIService
    from ecmwf_downloader.infrastructure.secrets import SecretStore

    options = []
    real_client = httpx.Client

    def response(request):
        assert request.url.host == "ai.example.invalid"
        return httpx.Response(200, json={
            "choices": [{"index": 0, "finish_reason": "stop",
                         "message": {"role": "assistant", "content": "{\"ok\": true}"}}],
        })

    class Client(real_client):
        def __init__(self, **kwargs):
            options.append(kwargs)
            super().__init__(transport=httpx.MockTransport(response))

    monkeypatch.setattr(httpx, "Client", Client)
    service = AIService(AppSettings(), SecretStore(tmp_path / "secrets.yaml"))
    before = service.secrets.path.read_bytes()
    service.test_connection(base_url="https://ai.example.invalid/v1", model="fixture",
                            api_key="fixture", json_mode=True,
                            network=NetworkProxySettings(mode="manual", url=PROXY))
    assert options == [{"proxy": PROXY, "trust_env": True, "verify": True}]
    assert service.secrets.path.read_bytes() == before
