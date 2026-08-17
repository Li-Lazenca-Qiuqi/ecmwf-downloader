"""Build generic CDS task plans from a schema-shaped request payload."""

from __future__ import annotations

import copy
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ecmwf_downloader.domain.models import SplitStrategy


@dataclass(frozen=True)
class PlannedTask:
    payload: dict[str, Any]
    filename: str
    output_path: Path


def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]


def _set_like_source(payload: dict[str, Any], key: str, source: Any) -> None:
    # CDS accepts lists for all of these fields.  Preserve scalar shape for
    # other arbitrary schema fields but normalize split dimensions to lists.
    payload[key] = source if isinstance(source, list) else [source]


def _safe_stem(dataset_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]+", "_", dataset_id).strip("_") or "dataset"


def _extension(payload: dict[str, Any]) -> str:
    value = payload.get("data_format") or payload.get("format") or "netcdf"
    value = str(value).lower()
    return ".nc" if value in {"netcdf", "netcdf4"} else ".grib" if value == "grib" else f".{value}"


class RequestBuilder:
    """Split only dimensions explicitly present in the generic payload."""

    def build(
        self,
        *,
        dataset_id: str,
        payload: dict[str, Any],
        output_dir: Path,
        strategy: SplitStrategy = SplitStrategy.NONE,
        filename: str | None = None,
    ) -> list[PlannedTask]:
        if not dataset_id.strip():
            raise ValueError("dataset_id 不能为空")
        if not isinstance(payload, dict):
            raise ValueError("request_payload 必须是 JSON 对象")

        year_key = "year" if "year" in payload else "years" if "years" in payload else None
        month_key = "month" if "month" in payload else "months" if "months" in payload else None
        years = _as_list(payload.get(year_key)) if year_key else []
        months = _as_list(payload.get(month_key)) if month_key else []

        if strategy == SplitStrategy.YEAR and not year_key:
            raise ValueError("按年拆分需要 request_payload 包含 year 字段")
        if strategy == SplitStrategy.MONTH and (not year_key or not month_key):
            raise ValueError("按月拆分需要 request_payload 同时包含 year 和 month 字段")
        if strategy == SplitStrategy.YEAR and not years:
            raise ValueError("year 不能为空")
        if strategy == SplitStrategy.MONTH and (not years or not months):
            raise ValueError("year/month 不能为空")

        plans: list[tuple[dict[str, Any], str]] = []
        if strategy == SplitStrategy.NONE:
            plans.append((copy.deepcopy(payload), ""))
        elif strategy == SplitStrategy.YEAR:
            for year in years:
                item = copy.deepcopy(payload)
                _set_like_source(item, year_key, year)  # type: ignore[arg-type]
                plans.append((item, str(year)))
        else:
            for year in years:
                for month in months:
                    item = copy.deepcopy(payload)
                    _set_like_source(item, year_key, year)  # type: ignore[arg-type]
                    _set_like_source(item, month_key, month)  # type: ignore[arg-type]
                    plans.append((item, f"{year}_{int(month):02d}"))

        output_dir = Path(output_dir).expanduser()
        extension = _extension(payload)
        base = filename or f"{_safe_stem(dataset_id)}_{hashlib.sha1(str(payload).encode()).hexdigest()[:8]}{extension}"
        base_path = Path(base)
        if base_path.suffix.lower() != extension:
            base_path = base_path.with_suffix(extension)
        result: list[PlannedTask] = []
        for index, (item, suffix) in enumerate(plans, start=1):
            if suffix:
                stem = base_path.stem
                name = f"{stem}_{suffix}{base_path.suffix}"
            else:
                name = base_path.name
            # A duplicate base name can only happen for an explicit filename
            # with no split; split outputs receive a deterministic suffix.
            if len(plans) > 1 and not suffix:
                name = f"{base_path.stem}_{index}{base_path.suffix}"
            result.append(PlannedTask(payload=item, filename=name, output_path=output_dir / name))
        return result
