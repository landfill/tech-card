"""피드백 저장/로드 테스트."""
import json
import os
import tempfile
from datetime import date

import pytest

from pipeline.feedback_store import load_feedback_since, save_feedback


@pytest.fixture
def data_dir():
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_save_feedback_creates_file(data_dir):
    save_feedback(data_dir, date(2025, 2, 25), "wrong_source", "RSS URL이 잘못됐어요")
    path = os.path.join(data_dir, "feedback", "2025-02-25.json")
    assert os.path.isfile(path)
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 1
    assert data[0]["type"] == "wrong_source"
    assert data[0]["content"] == "RSS URL이 잘못됐어요"
    assert "created_at" in data[0]


def test_save_feedback_appends(data_dir):
    save_feedback(data_dir, date(2025, 2, 25), "a", "첫번째")
    save_feedback(data_dir, date(2025, 2, 25), "b", "두번째")
    path = os.path.join(data_dir, "feedback", "2025-02-25.json")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    assert len(data) == 2
    assert data[0]["content"] == "첫번째"
    assert data[1]["content"] == "두번째"


def test_load_feedback_since(data_dir):
    save_feedback(data_dir, date(2025, 2, 20), "x", "20일")
    save_feedback(data_dir, date(2025, 2, 25), "y", "25일")
    # cutoff 2025-02-22 -> 25일만
    result = load_feedback_since(data_dir, date(2025, 2, 22))
    assert len(result) == 1
    assert result[0]["content"] == "25일"
    assert result[0]["_issue_date"] == "2025-02-25"


def test_load_feedback_since_empty_dir(data_dir):
    assert load_feedback_since(data_dir, date(2025, 2, 1)) == []
