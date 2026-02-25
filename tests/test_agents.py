"""에이전트 러너 테스트."""
import json
import tempfile
from pathlib import Path

import pytest

from pipeline.agents import load_skill, run_agent


@pytest.fixture
def skills_dir(tmp_path):
    (tmp_path / "analyze.md").write_text("---\nname: analyze\n---\n# Analyze\nClassify the items.", encoding="utf-8")
    return tmp_path


def test_load_skill_returns_content(skills_dir):
    content = load_skill(skills_dir, "analyze")
    assert "Analyze" in content
    assert "Classify" in content


def test_load_skill_missing_raises(skills_dir):
    with pytest.raises(FileNotFoundError, match="Skill not found"):
        load_skill(skills_dir, "nonexistent")


def test_run_agent_calls_llm(skills_dir):
    class MockLLM:
        def generate(self, system: str, user: str) -> str:
            assert "Analyze" in system
            data = json.loads(user)
            assert data["items"] == [1, 2]
            return '{"classified": true}'
    client = MockLLM()
    out = run_agent("analyze", {"items": [1, 2]}, skills_dir, client)
    assert out == '{"classified": true}'
