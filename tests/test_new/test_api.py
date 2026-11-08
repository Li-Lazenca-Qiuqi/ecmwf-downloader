from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from typer.testing import CliRunner

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import RequestScheduler
from ecmwf_downloader.config import AppSettings, load_settings
from ecmwf_downloader.infrastructure import yaml_file
from ecmwf_downloader.interfaces.cli import app as cli_app
from ecmwf_downloader.interfaces.http.app import create_app


@pytest.mark.parametrize("account_id", [None, "explicit-test-account"])
def test_api_add_account_preserves_id_and_hides_key(tmp_path: Path, account_id):
    container = AppContainer(AppSettings(database_path=tmp_path / "db.sqlite3", config_dir=tmp_path / "config"))
    payload = {"email": "test@example.com", "key": "test-secret-key", "url": "https://example.invalid"}
    if account_id is not None:
        payload["id"] = account_id

    with TestClient(create_app(container, with_worker=False)) as client:
        created = client.post("/api/v1/accounts", json=payload)
        assert created.status_code == 200
        account = created.json()
        if account_id is None:
            assert str(UUID(account["id"])) == account["id"]
        else:
            assert account["id"] == account_id
        assert account["email"] == payload["email"]
        assert account["status"] == "active"
        assert "key" not in account
        assert payload["key"] not in created.text

        listed = client.get("/api/v1/accounts")
        assert listed.status_code == 200
        assert listed.json()["items"] == [account]
        assert payload["key"] not in listed.text
        stored = container.secrets.get_account(account["id"])
        assert stored is not None and stored["key"] == payload["key"]


def test_api_create_preview_and_cancel(tmp_path: Path):
    container = AppContainer(AppSettings(database_path=tmp_path / "db.sqlite3", config_dir=tmp_path / "config"))
    with TestClient(create_app(container, with_worker=False)) as client:
        preview = client.post(
            "/api/v1/requests/preview",
            json={"dataset_id": "test", "request_payload": {"year": [2024], "month": [1, 2]}, "split_strategy": "month"},
        )
        assert preview.status_code == 200
        assert len(preview.json()["items"]) == 2
        created = client.post(
            "/api/v1/tasks",
            json={"dataset_id": "test", "request_payload": {"year": [2024]}},
        )
        assert created.status_code == 200
        task_id = created.json()["items"][0]["id"]
        assert created.json()["items"][0]["status"] == "queued"
        assert client.post(f"/api/v1/tasks/{task_id}/enqueue").status_code in {404, 405}
        assert client.post(f"/api/v1/tasks/{task_id}/cancel").json()["status"] == "cancelled"
        assert client.post("/api/v1/tasks/actions/delete", json={"task_ids": [task_id]}).json() == {"affected": 1}


def test_api_validation_uses_problem_json(tmp_path: Path):
    container = AppContainer(AppSettings(database_path=tmp_path / "db.sqlite3", config_dir=tmp_path / "config"))
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.post("/api/v1/tasks", json={"request_payload": {}})
        assert response.status_code == 422
        assert response.headers["content-type"].startswith("application/problem+json")


def test_api_rejects_ai_secret_in_public_settings(tmp_path: Path):
    container = AppContainer(AppSettings(database_path=tmp_path / "db.sqlite3", config_dir=tmp_path / "config"))
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch("/api/v1/settings", json={"values": {"ai": {"api_key": "do-not-store"}}})
        assert response.status_code == 422
        assert "secrets.yaml" in response.json()["detail"]
        app_config = tmp_path / "config" / "app.yaml"
        assert not app_config.exists() or "do-not-store" not in app_config.read_text(encoding="utf-8")

def test_validation_does_not_echo_credential_input(tmp_path):
    container=AppContainer(AppSettings(database_path=tmp_path/"db",config_dir=tmp_path/"config"))
    try:
        with TestClient(create_app(container,with_worker=False)) as client:
            invalid=client.post("/api/v1/accounts",json={"email":"test@example.invalid","key":["private-key-in-input"]})
            assert invalid.status_code==422 and "private-key-in-input" not in invalid.text
    finally:
        container.database.engine.dispose()



@pytest.fixture
def configured_container(tmp_path):
    path = tmp_path / "isolated-config" / "app.yaml"
    settings = load_settings(path.parent)
    settings.database_path = tmp_path / "requests.sqlite3"
    container = AppContainer(settings)
    yield container
    container.database.engine.dispose()


@pytest.mark.parametrize("patch", [
    {"requests": {"max_workers": 0}},
    {"requests": {"poll_interval": "5"}},
    {"requests": {"retry_delays": []}},
    {"requests": {"synthetic-token-as-field": "synthetic-key-as-value"}},
    {"ai": {"base_url": "https://user:synthetic-key-as-value@example.invalid/v1"}},
    {"ai": {"timeout": "synthetic-key-as-value"}},
])
def test_invalid_patch_keeps_settings_and_next_start(configured_container, patch, caplog):
    container = configured_container
    old_settings = container.settings
    old_config = container.config_path.read_bytes()
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch("/api/v1/settings", json={"values": patch})
        assert response.status_code == 422
        assert "synthetic-" not in response.text + caplog.text
        assert container.settings is old_settings
        assert container.config_path.read_bytes() == old_config
        assert load_settings(container.config_path.parent).requests == old_settings.requests


@pytest.mark.parametrize("target", ["app.yaml", "secrets.yaml"])
def test_failed_ai_save_preserves_both_files_and_runtime(configured_container, monkeypatch, target):
    container = configured_container
    container.secrets.update_ai({"api_key": "original-test-key"})
    container.config_path.write_bytes(b"# comment to preserve\n" + container.config_path.read_bytes())
    before = container.config_path.read_bytes()
    secret_path = container.secrets.path
    old_secret = secret_path.read_bytes()
    replace = yaml_file.os.replace

    def failed_replace(src, dest):
        if dest.name == target:
            raise OSError("synthetic-credential-in-error")
        replace(src, dest)

    monkeypatch.setattr(yaml_file.os, "replace", failed_replace)
    original_settings = container.settings
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch("/api/v1/ai/config", json={
            "enabled": True, "base_url": "https://example.invalid/v1",
            "model": "synthetic-model", "api_key": "synthetic-new-key",
        })
    assert response.status_code == 503
    assert "synthetic-" not in response.text
    assert container.config_path.read_bytes() == before
    assert secret_path.read_bytes() == old_secret
    assert container.settings is original_settings
    assert not list(container.config_path.parent.glob(".*.yaml.*"))


def test_api_updates_running_scheduler_and_cli_settings_load_at_restart(configured_container):
    container = configured_container
    scheduler = RequestScheduler(container)
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch("/api/v1/settings", json={"values": {
            "requests": {"max_workers": 2, "poll_interval": 7, "retry_delays": [1, 2]},
        }})
    assert response.status_code == 200
    assert scheduler.max_workers == 2
    assert container.settings.requests.poll_interval == 7
    assert container.tasks_repository.retry_delays == (1, 2)

    command = ["--config-dir", str(container.config_path.parent), "--database", str(container.settings.database_path)]
    runner = CliRunner()
    prior = container.config_path.read_bytes()
    result = runner.invoke(cli_app, [*command, "config", "set", "requests.max_workers", "synthetic-key"])
    assert result.exit_code == 2 and "synthetic-key" not in result.output
    assert container.config_path.read_bytes() == prior

    result = runner.invoke(cli_app, [*command, "config", "set", "requests.max_workers", "3"])
    assert result.exit_code == 0 and "重启" in result.output
    assert scheduler.max_workers == 2
    with TestClient(create_app(container, with_worker=False)) as client:
        response = client.patch("/api/v1/settings", json={"values": {"requests": {"poll_interval": 9}}})
        assert response.json()["requests"]["max_workers"] == 2
    reloaded = load_settings(container.config_path.parent)
    assert reloaded.requests.max_workers == 3 and reloaded.requests.poll_interval == 9


def test_concurrent_settings_saves_merge_latest_file(configured_container):
    container = configured_container
    other = AppContainer(container.settings)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(container.update_settings, {"requests": {"max_workers": 2}})
            second = pool.submit(other.update_settings, {"requests": {"poll_interval": 7}})
            first.result()
            second.result()
        settings = load_settings(container.config_path.parent).requests
        assert settings.max_workers == 2 and settings.poll_interval == 7
    finally:
        other.database.engine.dispose()
