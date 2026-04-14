"""Regression tests for local dev startup script."""
from pathlib import Path


def test_run_dev_script_derives_frontend_api_base_from_backend_port() -> None:
    script = Path("scripts/run-dev.sh").read_text(encoding="utf-8")

    assert 'VITE_API_BASE="${VITE_API_BASE:-http://localhost:$BACKEND_PORT}"' in script
    assert 'echo "프론트엔드 API 대상: $VITE_API_BASE"' in script
    assert 'VITE_API_BASE="$VITE_API_BASE" "$VITE_BIN"' in script


def test_run_dev_script_falls_back_to_shared_worktree_dependencies() -> None:
    script = Path("scripts/run-dev.sh").read_text(encoding="utf-8")

    assert 'COMMON_GIT_DIR="$(git rev-parse --git-common-dir 2>/dev/null || true)"' in script
    assert 'SHARED_ROOT="$(cd "$COMMON_GIT_DIR/.." && pwd)"' in script
    assert 'UVICORN_BIN="$SHARED_ROOT/.venv/bin/uvicorn"' in script
    assert 'VITE_BIN="$SHARED_ROOT/frontend/node_modules/.bin/vite"' in script
    assert '"$UVICORN_BIN" backend.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT"' in script
    assert 'VITE_API_BASE="$VITE_API_BASE" "$VITE_BIN"' in script
