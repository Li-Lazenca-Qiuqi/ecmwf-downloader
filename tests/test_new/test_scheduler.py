from pathlib import Path
import time

from ecmwf_downloader.application.container import AppContainer
from ecmwf_downloader.application.worker import DownloadScheduler
from ecmwf_downloader.config import AppSettings
from ecmwf_downloader.domain.models import TaskStatus
from ecmwf_downloader.infrastructure.cds import CDSProvider


def test_scheduler_executes_a_queued_task(tmp_path: Path, monkeypatch):
    container = AppContainer(AppSettings(database_path=tmp_path / "db.sqlite3", config_dir=tmp_path / "config"))
    container.accounts.add(email="test@example.com", key="secret", url="https://example.invalid")

    def fake_download(self, *, dataset_id, request_payload, target, cancel_check=None):
        target.write_bytes(b"ecmwf")
        return target

    monkeypatch.setattr(CDSProvider, "download", fake_download)
    task = container.tasks.create(dataset_id="test", request_payload={}, output_dir=tmp_path / "downloads")[0]
    container.tasks.enqueue(task.id)
    scheduler = DownloadScheduler(container, poll_interval=0.02)
    assert scheduler.start()
    try:
        for _ in range(100):
            current = container.tasks.get(task.id)
            if current and current.status in {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}:
                break
            time.sleep(0.02)
        assert current is not None
        assert current.status == TaskStatus.COMPLETED
        assert current.progress == 100
        assert Path(current.output_path).read_bytes() == b"ecmwf"
    finally:
        scheduler.stop()
