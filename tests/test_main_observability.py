"""Startup and access-log observability tests."""
import logging
from pathlib import Path

from backend import main as backend_main


def _access_record(path: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg='%s - "%s %s HTTP/%s" %s',
        args=("127.0.0.1:12345", "GET", path, "1.1", 200),
        exc_info=None,
    )


def test_status_access_filter_blocks_only_pipeline_status() -> None:
    filt = backend_main.SuppressStatusPollFilter()

    assert filt.filter(_access_record("/api/pipeline/status")) is False
    assert filt.filter(_access_record("/api/pipeline/status?date=2026-04-13")) is False
    assert filt.filter(_access_record("/api/pipeline/run")) is True
    assert filt.filter(_access_record("/api/pipeline/status-detail")) is True


def test_build_startup_summary_is_secret_safe(tmp_path: Path, monkeypatch) -> None:
    data_dir = tmp_path / "data"
    config_dir = tmp_path / "config"
    data_dir.mkdir()
    config_dir.mkdir()
    monkeypatch.setattr(backend_main, "get_data_dir", lambda: data_dir)
    monkeypatch.setattr(backend_main, "get_config_dir", lambda: config_dir)
    monkeypatch.setenv("SMTP_USER", "mailer@example.com")
    monkeypatch.setenv("SMTP_PASSWORD", "super-secret")
    monkeypatch.setenv("GOOGLE_API_KEY", "secret-api-key")

    summary = backend_main.build_startup_summary()

    assert "server_started" in summary
    assert str(data_dir) in summary
    assert str(config_dir) in summary
    assert "/api/pipeline/status access log suppressed" in summary
    assert "super-secret" not in summary
    assert "secret-api-key" not in summary
