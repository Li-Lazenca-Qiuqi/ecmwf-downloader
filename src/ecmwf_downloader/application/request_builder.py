"""Build generic CDS task plans from a schema-shaped request payload."""

from __future__ import annotations

import copy
import calendar
import json
import re
from dataclasses import dataclass
from typing import Any

from ecmwf_downloader.domain.models import SplitStrategy
from ecmwf_downloader.infrastructure.mirrors import FILE_MIRROR_IDS, ncar_key


@dataclass(frozen=True)
class PlannedTask:
    payload: dict[str, Any]
    label: str

def _as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple)) else [value]

def _set_like_source(payload: dict[str, Any], key: str, value: Any) -> None:
    # 拆分后仍使用原字段的标量或列表编码。
    payload[key] = [value] if isinstance(payload[key], (list, tuple)) else value

class RequestBuilder:
    """Split only dimensions explicitly present in the generic payload."""

    def build(
        self,
        *,
        dataset_id: str,
        payload: dict[str, Any],
        strategy: SplitStrategy = SplitStrategy.NONE,
        warnings: list[str] | None = None,
    ) -> list[PlannedTask]:
        if not dataset_id.strip():
            raise ValueError("dataset_id 不能为空")
        if not isinstance(payload, dict):
            raise ValueError("request_payload 必须是 JSON 对象")

        if dataset_id in FILE_MIRROR_IDS:
            if strategy != SplitStrategy.NONE: raise ValueError('NCAR 按已发布文件生成任务，不支持日期拆分')
            if set(payload) != {'object_key'}: raise ValueError('NCAR 请求仅接受 object_key 字段')
            keys = _as_list(payload.get('object_key'))
            if not keys: raise ValueError('请至少选择一个已发布的 NCAR 文件')
            keys = list(dict.fromkeys(ncar_key(key) for key in keys))
            return [PlannedTask({'object_key': key}, key.rsplit('/', 1)[-1]) for key in keys]
        if dataset_id == 'mirror-arco-era5':
            raise ValueError('ARCO 本地导出已移除，请选择 CDS 或 NCAR 文件来源')
        year_key = "year" if "year" in payload else "years" if "years" in payload else None
        month_key = "month" if "month" in payload else "months" if "months" in payload else None
        day_key = "day" if "day" in payload else "days" if "days" in payload else None
        years = _as_list(payload.get(year_key)) if year_key else []
        months = _as_list(payload.get(month_key)) if month_key else []
        days = _as_list(payload.get(day_key)) if day_key else []
        # 去重保序，防止重复日期产生同名输出。
        years, months, days = [list({json.dumps(value, sort_keys=True): value for value in values}.values()) for values in (years, months, days)]
        if strategy == SplitStrategy.DAY and (not years or not months or not days):
            raise ValueError("按日拆分需要非空的 year、month 和 day 字段")

        def date_number(value: Any, low: int, high: int, name: str) -> int:
            if isinstance(value, bool) or not re.fullmatch(r"\d+", str(value)):
                raise ValueError(f"{name} 必须是范围内的整数")
            number = int(value)
            if not low <= number <= high:
                raise ValueError(f"{name} 必须在 {low}–{high} 之间")
            return number

        if strategy != SplitStrategy.NONE:
            for year in years: date_number(year, 1, 9999, "year")
        if strategy in {SplitStrategy.MONTH, SplitStrategy.DAY}:
            for month in months: date_number(month, 1, 12, "month")
        if strategy == SplitStrategy.DAY:
            for day in days: date_number(day, 1, 31, "day")

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
        elif strategy == SplitStrategy.MONTH:
            for year in years:
                for month in months:
                    item = copy.deepcopy(payload)
                    _set_like_source(item, year_key, year)  # type: ignore[arg-type]
                    _set_like_source(item, month_key, month)  # type: ignore[arg-type]
                    plans.append((item, f"{year}_{int(month):02d}"))
        elif strategy == SplitStrategy.DAY:
            skipped = 0
            seen_dates = set()
            for year in years:
                for month in months:
                    for day in days:
                        date = (int(year), int(month), int(day))
                        if date[2] > calendar.monthrange(date[0], date[1])[1]:
                            skipped += 1
                            continue
                        if date in seen_dates:
                            continue
                        seen_dates.add(date)
                        item = copy.deepcopy(payload)
                        for key, value in ((year_key, year), (month_key, month), (day_key, day)):
                            _set_like_source(item, key, value)
                        plans.append((item, f"{date[0]:04d}_{date[1]:02d}_{date[2]:02d}"))
            if not plans:
                raise ValueError("所选日期没有有效的日历日期，无法拆分")
            if skipped and warnings is not None:
                warnings.append(f"已跳过 {skipped} 个不存在的日期组合（按实际日历计算）。")

        return [PlannedTask(item, dataset_id + (' · ' + suffix if suffix else '')) for item, suffix in plans]
