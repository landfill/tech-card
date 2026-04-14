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


def test_dedup_skips_llm_for_very_high_similarity():
    class NoCallLLM:
        def generate(self, system, user):
            raise AssertionError("LLM should not be called for very high similarity")

    candidates = [{"title": "Cursor 2.4 release", "summary": "New Cursor update"}]
    recent = [{"title": "Cursor 2.4 release", "summary": "New Cursor update"}]

    result = dedup(candidates, recent, NoCallLLM(), threshold=0.3)

    assert result == []


def test_dedup_reports_progress():
    class NoCallLLM:
        def generate(self, system, user):
            return "NO"

    events = []
    candidates = [{"title": f"Item {i}", "summary": "Unique"} for i in range(3)]

    result = dedup(
        candidates,
        [],
        NoCallLLM(),
        threshold=0.5,
        progress_callback=lambda detail: events.append(detail),
    )

    assert len(result) == 3
    assert events
    assert events[-1]["checked_candidates"] == 3
    assert events[-1]["total_candidates"] == 3
