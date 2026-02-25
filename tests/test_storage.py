"""레터/인덱스 경로 및 7일 날짜 유틸 테스트."""
from datetime import date, timedelta

import pytest

from pipeline.storage import index_path, letter_path, recent_7d_dates


def test_letter_path():
    """letter_path(date) -> data/letters/YYYY-MM-DD.md"""
    assert letter_path("data", date(2025, 2, 25)) == "data/letters/2025-02-25.md"


def test_index_path():
    """index_path(date) -> data/index/YYYY-MM-DD.json"""
    assert index_path("data", date(2025, 2, 25)) == "data/index/2025-02-25.json"


def test_recent_7d_dates():
    """당일 기준 과거 7일(당일 포함) 날짜 리스트."""
    d = date(2025, 2, 25)
    result = recent_7d_dates(d)
    assert len(result) == 7
    assert result[0] == date(2025, 2, 19)
    assert result[-1] == date(2025, 2, 25)
    for i in range(6):
        assert result[i + 1] - result[i] == timedelta(days=1)
