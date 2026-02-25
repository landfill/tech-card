"""체크포인트 저장/로드 테스트."""
import json
import os
import tempfile
from datetime import date

import pytest

from pipeline.checkpoint import (
    list_completed_stages,
    load_checkpoint,
    save_checkpoint,
)


@pytest.fixture
def checkpoint_dir():
    """임시 체크포인트 루트 디렉터리."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def test_save_and_load_checkpoint(checkpoint_dir):
    """save_checkpoint 후 load_checkpoint로 동일 payload 복원."""
    save_checkpoint(checkpoint_dir, date(2025, 2, 25), "collect", {"items": [1, 2, 3]})
    loaded = load_checkpoint(checkpoint_dir, date(2025, 2, 25), "collect")
    assert loaded == {"items": [1, 2, 3]}


def test_load_checkpoint_missing_returns_none(checkpoint_dir):
    """존재하지 않는 체크포인트는 None."""
    result = load_checkpoint(checkpoint_dir, date(2025, 2, 25), "analyze")
    assert result is None


def test_list_completed_stages(checkpoint_dir):
    """list_completed_stages는 해당 날짜에 저장된 stage 이름 목록 반환."""
    save_checkpoint(checkpoint_dir, date(2025, 2, 25), "collect", {})
    save_checkpoint(checkpoint_dir, date(2025, 2, 25), "analyze", {})
    stages = list_completed_stages(checkpoint_dir, date(2025, 2, 25))
    assert set(stages) == {"collect", "analyze"}
    # .json만 stage로 인식 (파일명에서 .json 제거)
    assert "collect" in stages and "analyze" in stages


def test_list_completed_stages_empty_dir(checkpoint_dir):
    """해당 날짜 디렉터리가 없으면 빈 리스트."""
    stages = list_completed_stages(checkpoint_dir, date(2025, 2, 25))
    assert stages == []
