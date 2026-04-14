"""Operational logging for integrations."""
import logging
from datetime import date
from pathlib import Path

import pytest

from pipeline import card_backgrounds, publish


@pytest.mark.parametrize(
    ("send_result", "expected_fragment"),
    [
        ({"sent": False, "recipients": 0, "error": "수신자 없음"}, "outcome=no_recipients"),
        ({"sent": False, "recipients": 1, "error": "SMTP 미설정 (스텁 모드)"}, "outcome=stub"),
        ({"sent": False, "recipients": 0, "error": "SMTP timeout"}, "outcome=failed"),
        ({"sent": True, "recipients": 2, "error": None}, "outcome=succeeded"),
    ],
)
def test_publish_logs_email_outcome(tmp_path: Path, monkeypatch, caplog, send_result: dict, expected_fragment: str) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    d = date(2026, 4, 13)
    letter_path = data_dir / "letters" / f"{d.isoformat()}.md"
    letter_path.parent.mkdir(parents=True, exist_ok=True)
    letter_path.write_text("# Letter", encoding="utf-8")

    monkeypatch.setattr(publish, "load_subscribers", lambda _: ["a@example.com"])
    monkeypatch.setattr(publish, "send_email", lambda *_: send_result)
    caplog.set_level(logging.INFO, logger="pipeline.publish")

    publish.publish(d.isoformat(), data_dir)

    messages = [record.getMessage() for record in caplog.records]
    assert any("event=integration_email" in message and expected_fragment in message for message in messages)


def test_generate_card_background_logs_missing_config(tmp_path: Path, monkeypatch, caplog) -> None:
    monkeypatch.setattr(card_backgrounds, "load_image_config", lambda _: None)
    caplog.set_level(logging.INFO, logger="pipeline.card_backgrounds")

    result = card_backgrounds.generate_card_background("# Letter", str(tmp_path), date(2026, 4, 13), None, None, tmp_path)

    assert result is None
    assert any("event=integration_image outcome=missing_config" in record.getMessage() for record in caplog.records)


def test_generate_card_background_logs_api_failure(tmp_path: Path, monkeypatch, caplog) -> None:
    monkeypatch.setattr(card_backgrounds, "load_image_config", lambda _: {"api_key": "x", "model": "m"})
    monkeypatch.setattr(card_backgrounds, "extract_theme", lambda *args, **kwargs: "ai chips")
    monkeypatch.setattr(card_backgrounds, "_generate_gemini_image", lambda *args, **kwargs: False)
    caplog.set_level(logging.INFO, logger="pipeline.card_backgrounds")

    result = card_backgrounds.generate_card_background("# Letter", str(tmp_path), date(2026, 4, 13), None, None, tmp_path)

    assert result is None
    assert any("event=integration_image outcome=failed" in record.getMessage() for record in caplog.records)
