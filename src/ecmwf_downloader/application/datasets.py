"""Dataset metadata facade with an offline fallback for the local UI."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any, Optional

from ecmwf_downloader.infrastructure.cds import CDSProvider
from ecmwf_downloader.infrastructure.datastores import DatastoresProvider


def _jsonable(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value):
        return {key: _jsonable(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): _jsonable(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    return value


class DatasetService:
    def list(self) -> list[dict[str, Any]]:
        return [{"id": item, "title": item, "source": "CDS"} for item in CDSProvider.DATASETS]

    def schema(self, dataset_id: str, account: Optional[dict[str, Any]] = None) -> dict[str, Any]:
        # The official Datastores client is optional at runtime.  Use it when
        # credentials are available, otherwise expose a useful schema-shaped
        # fallback so offline request editing still works.
        if account and account.get("key"):
            try:
                schema = DatastoresProvider(
                    url=account.get("url", "https://cds.climate.copernicus.eu/api"),
                    key=account["key"],
                ).schema(dataset_id)
                return _jsonable(schema)
            except Exception:
                pass
        return {
            "collection_id": dataset_id,
            "title": dataset_id,
            "description": "CDS 数据集请求字段；可直接编辑原始 request payload。",
            "fields": [
                {"name": "product_type", "label": "product_type", "field_type": "string_list", "required": False, "values": ["reanalysis"]},
                {"name": "variable", "label": "variable", "field_type": "string_list", "required": True, "values": []},
                {"name": "year", "label": "year", "field_type": "integer_list", "required": True, "values": []},
                {"name": "month", "label": "month", "field_type": "string_list", "required": True, "values": [f"{i:02d}" for i in range(1, 13)]},
                {"name": "day", "label": "day", "field_type": "string_list", "required": False, "values": [f"{i:02d}" for i in range(1, 32)]},
                {"name": "time", "label": "time", "field_type": "string_list", "required": False, "values": ["00:00", "06:00", "12:00", "18:00"]},
                {"name": "data_format", "label": "data_format", "field_type": "string_single", "required": False, "values": ["netcdf", "grib"]},
                {"name": "download_format", "label": "download_format", "field_type": "string_single", "required": False, "values": ["unarchived", "zip"]},
            ],
            "constraints": {},
        }

    def constraints(self, dataset_id: str, selection: dict[str, Any], account: Optional[dict[str, Any]] = None) -> dict[str, list[str]]:
        if account and account.get("key"):
            try:
                return DatastoresProvider(
                    url=account.get("url", "https://cds.climate.copernicus.eu/api"),
                    key=account["key"],
                ).constraints(dataset_id, selection)
            except Exception:
                pass
        return {}
