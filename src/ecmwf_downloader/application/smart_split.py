"""按有效时间点数分割原有请求字段的笛卡尔积。"""

from bisect import bisect_right
import calendar
from copy import deepcopy
from math import prod
import re
from typing import Any

from ecmwf_downloader.domain.schema import TIME_AXES

Axes = dict[str, tuple[int, ...]]


def _time_number(axis: str, raw: Any) -> int:
    text = str(raw)
    if axis == 'time':
        match = re.fullmatch(r'(\d{1,2})(?::(\d{2})(?::(\d{2}))?)?', text)
        if match:
            hour, minute, second = (int(part or 0) for part in match.groups())
            if hour < 24 and minute < 60 and second < 60:
                return hour * 3600 + minute * 60 + second
        raise ValueError('智能拆分需要整数小时或 HH:MM 时次')
    limit = {'year': 9999, 'month': 12, 'day': 31}[axis]
    if not re.fullmatch(r'\d+', text) or not 1 <= int(text) <= limit:
        raise ValueError(f'智能拆分要求 {axis} 为 1–{limit} 之间的整数')
    return int(text)


def _weights(axes: Axes) -> dict[str, list[int]]:
    """统计每个轴值覆盖的有效点数，不展开全部时次组合。"""
    if 'day' not in axes:
        total = prod(len(values) for values in axes.values())
        return {axis: [total // len(values)] * len(values) for axis, values in axes.items()}

    years, months, days = (axes[axis] for axis in ('year', 'month', 'day'))
    year_weights = [0] * len(years)
    month_weights = [0] * len(months)
    day_endings = [0] * (len(days) + 1)
    for y, year in enumerate(years):
        for m, month in enumerate(months):
            valid = bisect_right(days, calendar.monthrange(year, month)[1])
            year_weights[y] += valid
            month_weights[m] += valid
            day_endings[valid] += 1
    day_weights = [0] * len(days)
    valid_months = 0
    for d in reversed(range(len(days))):
        valid_months += day_endings[d + 1]
        day_weights[d] = valid_months

    time_count = len(axes.get('time', (0,)))
    weights = {axis: [count * time_count for count in counts] for axis, counts in
               [('year', year_weights), ('month', month_weights), ('day', day_weights)]}
    if 'time' in axes:
        weights['time'] = [sum(year_weights)] * time_count
    return weights


def _best_cut(weights: dict[str, list[int]], total: int, parts: int) -> tuple[str, int, int]:
    # 每个候选切口按有效点数分配左右份数，优先压低每份的平均负载上界。
    best = None
    for axis, counts in weights.items():
        left = 0
        for index, count in enumerate(counts[:-1], 1):
            left += count
            right = total - left
            if not left or not right:
                continue
            low = max(1, parts - right)
            high = min(parts - 1, left)
            target = parts * left // total
            for quota in (max(low, min(high, target)), max(low, min(high, target + 1))):
                score = (max(left / quota, right / (parts - quota)), abs(parts - 2 * quota))
                if best is None or score < best[0]:
                    best = (score, axis, index, quota)
    assert best is not None  # 至少两个有效点时必存在可分割的轴。
    return best[1], best[2], best[3]


def smart_split(payload: dict[str, Any], count: int, warnings: list[str] | None) -> list[dict[str, Any]]:
    if {'date', 'dates', 'date_range'} & payload.keys():
        raise ValueError('智能拆分暂不支持日期区间形式的时间字段')
    keys = {}
    raw_values = {}
    for axis, aliases in TIME_AXES.items():
        fields = [key for key in aliases if key in payload]
        if len(fields) > 1:
            raise ValueError(f'智能拆分无法确定重复的 {axis} 时间字段')
        if fields:
            key = keys[axis] = fields[0]
            values = payload[key]
            values = values if isinstance(values, (list, tuple)) else [values]
            normalized: dict[int, Any] = {}
            for value in values:
                normalized.setdefault(_time_number(axis, value), value)
            if not normalized:
                raise ValueError(f'智能拆分要求 {key} 非空')
            raw_values[axis] = normalized
    if not keys:
        raise ValueError('当前请求需要可明确拆分的年月日或时次字段')
    if 'day' in keys and not {'year', 'month'} <= keys.keys():
        raise ValueError('智能拆分日期需要同时提供 year、month 和 day 字段')

    axes = {axis: tuple(sorted(values)) for axis, values in raw_values.items()}
    available = sum(next(iter(_weights(axes).values())))
    if not available:
        raise ValueError('所选日期没有有效的日历日期，无法拆分')
    if count > available:
        raise ValueError(f'当前选择最多可拆成 {available} 份，请减少目标份数')
    if warnings is not None and 'day' in axes:
        possible = prod(len(axes[axis]) for axis in ('year', 'month', 'day'))
        skipped = possible - available // len(axes.get('time', (0,)))
        if skipped:
            warnings.append(f'计算有效时间点时已忽略 {skipped} 个不存在的日历日期组合。')

    def encode(box: Axes) -> dict[str, Any]:
        result = deepcopy(payload)
        for axis, values in box.items():
            key = keys[axis]
            raw = [raw_values[axis][value] for value in values]
            result[key] = raw if isinstance(payload[key], (list, tuple)) else raw[0]
        return result

    plans = []
    pending = [(axes, count)]
    while pending:
        box, parts = pending.pop()
        weights = _weights(box)
        # 删除在本分区内没有任何有效组合的时间值。
        box = {axis: tuple(value for value, weight in zip(values, weights[axis]) if weight)
               for axis, values in box.items()}
        weights = {axis: [weight for weight in values if weight] for axis, values in weights.items()}
        if parts == 1:
            plans.append(encode(box))
            continue
        total = sum(next(iter(weights.values())))
        time_count = len(box.get('time', (0,)))
        if 'time' in box and total // time_count >= parts:
            # 日期足够时优先分割日期，保留每个日期的全部时次。
            total //= time_count
            weights = {axis: [weight // time_count for weight in counts]
                       for axis, counts in weights.items() if axis != 'time'}
        varying = [axis for axis, counts in weights.items() if len(counts) > 1]
        if len(varying) == 1:
            axis = varying[0]
            size, extra = divmod(len(box[axis]), parts)
            offset = 0
            for part in range(parts):
                end = offset + size + (part < extra)
                plans.append(encode({**box, axis: box[axis][offset:end]}))
                offset = end
            continue
        axis, cut, quota = _best_cut(weights, total, parts)
        pending.append(({**box, axis: box[axis][cut:]}, parts - quota))
        pending.append(({**box, axis: box[axis][:cut]}, quota))
    return plans
