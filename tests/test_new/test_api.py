from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import IntegrityError
from typer.testing import CliRunner

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import RequestScheduler
from ecmwf_downloader.config import AppSettings, load_settings
from ecmwf_downloader.infrastructure import yaml_file
from ecmwf_downloader.infrastructure.db import Database, TaskRow
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


def test_named_batch_preserves_positions_and_legacy_rows(tmp_path):
    settings = AppSettings(database_path=tmp_path / "requests.sqlite3", config_dir=tmp_path / "config")
    old_database = Database(settings.database_path)
    try:
        TaskRow.__table__.create(old_database.engine)
        now = datetime.now(timezone.utc)
        with old_database.session() as session:
            session.execute(TaskRow.__table__.insert().values(
                id="legacy", dataset_id="test", request_payload="{}", title="原请求名",
                status="completed", created_at=now, updated_at=now,
            ))
    finally:
        old_database.engine.dispose()

    def make_container():
        container = AppContainer(settings)
        return container, TestClient(create_app(container, with_worker=False))

    container, client = make_container()
    try:
        with client:
            legacy = client.get("/api/v1/tasks/legacy").json()
            assert legacy["title"] == "原请求名" and legacy["batch"] is None

            body = {"dataset_id": "test", "name": " 地表温度 ", "split_strategy": "month",
                    "request_payload": {"year": ["2024"], "month": ["01", "02", "03"]}}
            response = client.post("/api/v1/tasks", json=body)
            assert response.status_code == 200
            first, second, third = response.json()["items"]
            batch_id = first["batch"]["batch_id"]
            for position, task in enumerate((first, second, third), start=1):
                assert task["batch"] == {"batch_id": batch_id, "name": "地表温度", "position": position, "total": 3}
            assert first["title"] == "test · 2024_01"
            page = client.get("/api/v1/tasks", params={"search": "地表温度", "limit": 1, "offset": 1}).json()
            assert page["total"] == 3 and page["items"][0]["id"] == second["id"]

            assert client.post(f"/api/v1/tasks/{first['id']}/cancel").status_code == 200
            assert client.delete(f"/api/v1/tasks/{first['id']}").status_code == 200
            assert client.post(f"/api/v1/tasks/{third['id']}/cancel").status_code == 200
            retried = client.post(f"/api/v1/tasks/{third['id']}/retry").json()
            assert retried["batch"] == third["batch"]

            single = client.post("/api/v1/tasks", json={"dataset_id": "test", "request_payload": {}}).json()["items"][0]
            assert single["batch"]["name"] == "test" and single["batch"]["total"] == 1
            assert single["batch"]["batch_id"] != batch_id
    finally:
        container.database.engine.dispose()

    container, client = make_container()
    try:
        with client:
            page = client.get("/api/v1/tasks", params={"search": "地表温度", "status": "queued"}).json()
            assert [task["id"] for task in page["items"]] == [second["id"], third["id"]]
            assert [task["batch"]["position"] for task in page["items"]] == [2, 3]
            assert all(task["batch"]["total"] == 3 for task in page["items"])
            assert client.get("/api/v1/tasks/legacy").json() == legacy
    finally:
        container.database.engine.dispose()


def test_ncar_batch_rolls_back_if_member_cannot_be_saved(tmp_path):
    settings = AppSettings(database_path=tmp_path / "requests.sqlite3", config_dir=tmp_path / "config")
    container = AppContainer(settings)
    try:
        with container.database.engine.begin() as connection:
            connection.exec_driver_sql("""
                CREATE TRIGGER reject_second_member BEFORE INSERT ON request_batch_items
                WHEN NEW.position = 2 BEGIN SELECT RAISE(ABORT, 'test failure'); END
            """)
        body = {"dataset_id": "mirror-ncar-era5", "name": "NCAR 地表数据",
                "request_payload": {"object_key": ["e5.oper.an.sfc/202401/first.nc", "e5.oper.an.sfc/202401/second.nc"]}}
        with TestClient(create_app(container, with_worker=False)) as client:
            with pytest.raises(IntegrityError, match="test failure"):
                client.post("/api/v1/tasks", json=body)
            assert client.get("/api/v1/tasks").json()["total"] == 0
            assert container.tasks_repository.events_after() == []
            with container.database.engine.begin() as connection:
                assert connection.exec_driver_sql("SELECT count(*) FROM request_batch_items").scalar_one() == 0
                connection.exec_driver_sql("DROP TRIGGER reject_second_member")
            items = client.post("/api/v1/tasks", json=body).json()["items"]
            assert [task["batch"]["position"] for task in items] == [1, 2]
            assert {task["batch"]["name"] for task in items} == {"NCAR 地表数据"}
            assert len({task["batch"]["batch_id"] for task in items}) == 1
    finally:
        container.database.engine.dispose()


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


def test_queue_cursor_and_batch_links_survive_changes(tmp_path):
    settings = AppSettings(database_path=tmp_path / "requests.sqlite3", config_dir=tmp_path / "config")
    container = AppContainer(settings)
    body = {
        "dataset_id": "test", "name": "同名请求", "split_strategy": "day",
        "request_payload": {"year": ["2024"], "month": ["01"], "day": [f"{day:02}" for day in range(1, 24)]},
    }
    with TestClient(create_app(container, with_worker=False)) as client:
        original = client.post("/api/v1/tasks", json=body).json()["items"]
        assert len(original) == 23
        batch_id = original[0]["batch"]["batch_id"]
        page = client.get("/api/v1/tasks", params={"cursor": "", "limit": 20}).json()
        assert [row["id"] for row in page["items"]] == [row["id"] for row in original[:20]]

        client.post("/api/v1/tasks", json={**body, "split_strategy": "none"}).raise_for_status()
        deleted = original[19]["id"]
        client.post(f"/api/v1/tasks/{deleted}/cancel").raise_for_status()
        client.delete(f"/api/v1/tasks/{deleted}").raise_for_status()
        tail = client.get("/api/v1/tasks", params={"cursor": page["next_cursor"], "limit": 20}).json()
        assert [row["id"] for row in tail["items"]] == [row["id"] for row in original[20:]]
        assert tail["next_cursor"] is None
        assert client.get("/api/v1/tasks", params={"cursor": "invalid"}).status_code == 422

        with container.database.session(immediate=True) as session:
            row = session.get(TaskRow, original[-1]["id"])
            row.status = "completed"
            row.results = '[{"url":"https://example.test/last"}]'
        batch = client.get(f"/api/v1/request-batches/{batch_id}").json()
        assert batch["name"] == body["name"] and batch["total"] == 23
        assert [item["position"] for item in batch["items"]] == [*range(1, 20), 21, 22, 23]
        assert [link for item in batch["items"] for link in item["links"]] == ["https://example.test/last"]
        assert client.get("/api/v1/request-batches/missing").status_code == 404


def test_busy_explicit_account_cannot_create_another_batch(tmp_path):
    settings = AppSettings(database_path=tmp_path / "requests.sqlite3", config_dir=tmp_path / "config")
    container = AppContainer(settings)
    with TestClient(create_app(container, with_worker=False)) as client:
        account = client.post("/api/v1/accounts", json={
            "email": "fixture@example.test", "key": "fixture", "url": "https://example.test",
        }).json()
        body = {"dataset_id": "test", "request_payload": {"year": ["2024"]}, "account_ids": [account["id"]]}
        client.post("/api/v1/tasks", json=body).raise_for_status()
        claimed = container.tasks_repository.claim_next("worker", account_id=account["id"])
        assert claimed.account_id == account["id"]
        assert client.get("/api/v1/accounts").json()["items"][0]["is_busy"]
        rejected = client.post("/api/v1/tasks", json=body)
        assert rejected.status_code == 422 and "繁忙" in rejected.json()["detail"]
        assert client.get("/api/v1/tasks").json()["total"] == 1


def test_request_preset_does_not_replace_legacy_template(tmp_path):
    settings = AppSettings(database_path=tmp_path / "requests.sqlite3", config_dir=tmp_path / "config")
    container = AppContainer(settings)
    with TestClient(create_app(container, with_worker=False)) as client:
        client.post("/api/v1/templates", json={"name": "现有模板", "payload": {"year": ["2024"]}}).raise_for_status()
        preset = {"kind": "ecmwf-request-preset-v1", "editor_values": {"year": ["2025"]}}
        assert client.post("/api/v1/templates", json={"name": "现有模板", "payload": preset}).status_code == 422
        saved = client.post("/api/v1/templates", json={"name": "新预设", "payload": preset}).json()
    reopened = AppContainer(settings)
    assert reopened.templates.get(saved["id"])["payload"] == preset
