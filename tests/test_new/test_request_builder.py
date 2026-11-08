from datetime import date
from itertools import product
import json
from pathlib import Path

import pytest

from ecmwf_downloader.application.request_builder import RequestBuilder
from ecmwf_downloader.domain.models import SplitStrategy


def test_month_split_creates_one_task_per_year_month(tmp_path: Path):
    plans = RequestBuilder().build(
        dataset_id="reanalysis-era5-pressure-levels",
        payload={"year": [2024, 2025], "month": [1, 2], "variable": ["temperature"]},
        strategy=SplitStrategy.MONTH,
    )
    assert len(plans) == 4
    assert plans[0].payload["year"] == [2024]
    assert plans[0].payload["month"] == [1]
    assert plans[-1].label.endswith("2025_02")


def test_split_requires_dimensions(tmp_path: Path):
    with pytest.raises(ValueError, match="year"):
        RequestBuilder().build(
            dataset_id="test",
            payload={"month": [1]},
                strategy=SplitStrategy.YEAR,
        )


def test_smart_split_divides_ten_days_and_preserves_parameters():
    payload = {'year': 2024, 'month': ['01'], 'day': [f'{day:02}' for day in range(1, 11)],
               'time': ['00:00', '12:00'], 'variable': ['t'], 'area': [31, 120, 30, 121]}
    plans = RequestBuilder().build(dataset_id='test', payload=payload, strategy=SplitStrategy.SMART, split_count=3)
    assert [len(plan.payload['day']) * len(plan.payload['time']) for plan in plans] == [8, 6, 6]
    assert [day for plan in plans for day in plan.payload['day']] == payload['day']
    for plan in plans:
        assert plan.payload == {**payload, 'day': plan.payload['day']}
    assert [plan.label for plan in plans] == [f'test · 第 {index}/3 份' for index in (1, 2, 3)]


def test_smart_split_covers_sparse_dates_and_hours_exactly():
    payload = {'years': [2024, 2023], 'months': ['03', '02'], 'days': ['31', '29', '01'], 'hours': [18, 0]}

    def points(selection):
        result = set()
        for year, month, day, hour in product(*(selection[key] for key in payload)):
            try:
                result.add((date(year, int(month), int(day)), hour))
            except ValueError:
                continue
        return result

    expected = points(payload)
    assert (date(2024, 2, 29), 0) in expected
    for count in (3, 7, len(expected)):
        warnings = []
        plans = RequestBuilder().build(dataset_id='test', payload=payload, strategy=SplitStrategy.SMART,
                                       split_count=count, warnings=warnings)
        parts = [points(plan.payload) for plan in plans]
        assert len(parts) == count and all(parts)
        assert sum(map(len, parts)) == len(expected) and set.union(*parts) == expected
        assert warnings and '不存在' in warnings[0]


@pytest.mark.parametrize('payload,count,message', [
    ({'time': ['00:00', '12:00']}, 1, '大于等于 2'),
    ({'time': ['00:00', '12:00']}, 2.5, '整数'),
    ({'time': ['00:00', '12:00']}, 3, '最多可拆成 2 份'),
    ({'year': [2023], 'month': [2], 'day': [29]}, 2, '没有有效'),
    ({'date': '2024-01-01/2024-01-10'}, 2, '时间'),
    ({'year': [2024], 'day': [1, 2]}, 2, '同时提供'),
])
def test_smart_split_rejects_unrepresentable_requests(payload, count, message):
    with pytest.raises(ValueError, match=message):
        RequestBuilder().build(dataset_id='test', payload=payload, strategy=SplitStrategy.SMART, split_count=count)


def test_cli_smart_split_previews_and_creates_the_same_plan(tmp_path):
    from typer.testing import CliRunner
    from ecmwf_downloader.interfaces.cli.app import app

    runner = CliRunner()
    options = ['--config-dir', str(tmp_path / 'config'), '--database', str(tmp_path / 'db')]
    args = ['--dataset', 'test', '--set', 'time=["00:00","06:00","12:00"]', '--split', 'smart', '--split-count', '2']
    preview = runner.invoke(app, [*options, 'request', 'preview', *args])
    created = runner.invoke(app, [*options, 'task', 'create', *args, '--json'])
    assert preview.exit_code == created.exit_code == 0
    expected = [{'time': ['00:00', '06:00']}, {'time': ['12:00']}]
    assert [item['request_payload'] for item in json.loads(preview.stdout)] == expected
    assert [item['request_payload'] for item in json.loads(created.stdout)] == expected
