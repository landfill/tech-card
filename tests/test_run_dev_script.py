"""Regression tests for local dev startup script."""
from pathlib import Path


def test_run_dev_script_derives_frontend_api_base_from_backend_port() -> None:
    script = Path("scripts/run-dev.sh").read_text(encoding="utf-8")

    assert 'VITE_API_BASE="${VITE_API_BASE:-http://localhost:$BACKEND_PORT}"' in script
    assert 'echo "프론트엔드 API 대상: $VITE_API_BASE"' in script
    assert 'VITE_API_BASE="$VITE_API_BASE" npm run dev' in script
