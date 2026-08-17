from pathlib import Path

import pytest

from ecmwf_downloader.application.request_builder import RequestBuilder
from ecmwf_downloader.domain.models import SplitStrategy


def test_month_split_creates_one_task_per_year_month(tmp_path: Path):
    plans = RequestBuilder().build(
        dataset_id="reanalysis-era5-pressure-levels",
        payload={"year": [2024, 2025], "month": [1, 2], "variable": ["temperature"]},
        output_dir=tmp_path,
        strategy=SplitStrategy.MONTH,
    )
    assert len(plans) == 4
    assert plans[0].payload["year"] == [2024]
    assert plans[0].payload["month"] == [1]
    assert plans[-1].filename.endswith("2025_02.nc")


def test_split_requires_dimensions(tmp_path: Path):
    with pytest.raises(ValueError, match="year"):
        RequestBuilder().build(
            dataset_id="test",
            payload={"month": [1]},
            output_dir=tmp_path,
            strategy=SplitStrategy.YEAR,
        )
