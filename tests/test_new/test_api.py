from pathlib import Path

from fastapi.testclient import TestClient

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.interfaces.http.app import create_app


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
            json={"dataset_id": "test", "request_payload": {"year": [2024]}, "enqueue": False},
        )
        assert created.status_code == 200
        task_id = created.json()["items"][0]["id"]
        assert client.post(f"/api/v1/tasks/{task_id}/enqueue").json()["status"] == "queued"
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
