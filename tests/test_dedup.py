"""중복 제거 테스트."""
import pytest

from pipeline.dedup import _similarity, dedup


def test_similarity_same():
    assert _similarity("Cursor 2.4 release", "Cursor 2.4 release") >= 0.99


def test_similarity_different():
    assert _similarity("Python tips", "Reddit news") < 0.5


def test_dedup_keeps_all_when_no_recent():
    class NoCallLLM:
        def generate(self, system, user):
            return "NO"
    candidates = [{"title": "A", "summary": "a"}, {"title": "B", "summary": "b"}]
    result = dedup(candidates, [], NoCallLLM(), threshold=0.5)
    assert len(result) == 2


def test_dedup_drops_high_similarity_with_llm_yes():
    class YesLLM:
        def generate(self, system, user):
            return "YES"
    candidates = [{"title": "Cursor 2.4 release", "summary": "New Cursor update"}]
    recent = [{"title": "Cursor 2.4 release", "summary": "New Cursor update"}]
    result = dedup(candidates, recent, YesLLM(), threshold=0.3)
    assert len(result) == 0
