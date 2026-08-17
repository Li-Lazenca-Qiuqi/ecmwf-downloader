"""CDS provider adapter with a UI-independent download contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable, Optional

import cdsapi


class ProviderError(RuntimeError):
    pass


class DownloadCancelled(ProviderError):
    pass


class CDSProvider:
    DATASETS = [
        "reanalysis-era5-pressure-levels",
        "reanalysis-era5-single-levels",
        "reanalysis-era5-land",
        "reanalysis-era5-land-monthly-means",
        "reanalysis-era5-monthly-means",
    ]

    def __init__(self, account: dict[str, Any]):
        if not account.get("key"):
            raise ProviderError("账号缺少 API Key")
        self.account = account

    def _client(self):
        try:
            return cdsapi.Client(
                url=self.account.get("url", "https://cds.climate.copernicus.eu/api"),
                key=self.account["key"],
                timeout=1800,
                verify=True,
            )
        except Exception as exc:  # pragma: no cover - exercised with integration credentials
            raise ProviderError(f"CDS 客户端初始化失败: {exc}") from exc

    def download(
        self,
        *,
        dataset_id: str,
        request_payload: dict[str, Any],
        target: Path,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> Path:
        if cancel_check and cancel_check():
            raise DownloadCancelled("任务已取消")
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            result = self._client().retrieve(dataset_id, request_payload)
            if cancel_check and cancel_check():
                raise DownloadCancelled("任务已取消")
            result.download(str(target))
            if cancel_check and cancel_check():
                raise DownloadCancelled("任务已取消")
            return target
        except DownloadCancelled:
            raise
        except Exception as exc:
            raise ProviderError(f"CDS 下载失败: {exc}") from exc

    def check_connection(self) -> tuple[bool, str]:
        try:
            client = self._client()
            response = client.session.get(
                f"{self.account.get('url', 'https://cds.climate.copernicus.eu/api')}/tasks/",
                timeout=30,
            )
            if response.status_code >= 400:
                return False, f"HTTP {response.status_code}"
            return True, "连接正常"
        except Exception as exc:
            return False, str(exc)
