"""Startup and access-log observability tests."""
import logging
from pathlib import Path

from backend import main as backend_main


def _access_record(path: str, method: str = "GET", status_code: int = 200) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %s',
        args=("127.0.0.1:12345", method, path, "1.1", status_code),
        exc_info=None,
    )


def test_status_access_filter_blocks_noisy_successful_ui_reads() -> None:
    filt = backend_main.SuppressStatusPollFilter()

    assert filt.filter(_access_record("/api/pipeline/status")) is False
    assert filt.filter(_access_record("/api/pipeline/status?date=2026-04-13")) is False
    assert filt.filter(_access_record("/api/letters")) is False
    assert filt.filter(_access_record("/api/letters/2026-04-13/info")) is False
    assert filt.filter(_access_record("/api/weekly")) is False
    assert filt.filter(_access_record("/api/weekly/2026-W15/meta")) is False
    assert filt.filter(_access_record("/api/pipeline/run")) is True
    assert filt.filter(_access_record("/api/weekly/run", method="POST", status_code=202)) is True
    assert filt.filter(_access_record("/api/letters", status_code=500)) is True
    assert filt.filter(_access_record("/api/pipeline/status-detail")) is True


def test_build_startup_summary_is_secret_safe(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()
    (config_dir / "llm.yaml").write_text("provider: google\nmodel: gemini-3-flash-preview\n", encoding="utf-8")
    monkeypatch.setattr(backend_main, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(backend_main, "get_config_dir", lambda: config_dir)
    monkeypatch.setenv("SMTP_USER", "mailer@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "super-secret")
    monkeypatch.setenv("GOOGLE_API_KEY", "secret-api-key")

    summary = backend_main.build_startup_summary()

    assert "server_started" in summary
    assert str(data_dir) in summary
    assert str(config_dir) in summary
    assert "noisy_ui_access_logs_suppressed=/api/letters,/api/weekly,/api/pipeline/status" in summary
    assert "llm_provider=google" in summary
    assert "llm_model=gemini-3-flash-preview" in summary
    assert "super-secret" not in summary
    assert "secret-api-key" not in summary


def test_application_logging_suppresses_noisy_sdk_info_loggers() -> None:
    backend_main._configure_application_logging()

    assert logging.getLogger("httpx").level >= logging.WARNING
    assert logging.getLogger("httpcore").level >= logging.WARNING
    assert logging.getLogger("openai").level >= logging.WARNING
    assert logging.getLogger("openai._base_client").level >= logging.WARNING
