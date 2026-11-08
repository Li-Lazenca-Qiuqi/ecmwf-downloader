from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
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
