#!/usr/bin/env bash
# 백엔드(uvicorn) + 프론트엔드(vite) 한 번에 실행. 종료 시 Ctrl+C 로 둘 다 정리됨.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"
VITE_API_BASE="${VITE_API_BASE:-/api}"
COMMON_GIT_DIR="$(git rev-parse --git-common-dir 2>/dev/null || true)"
SHARED_ROOT=""
if [ -n "$COMMON_GIT_DIR" ] && [ "$(basename "$COMMON_GIT_DIR")" = ".git" ]; then
  SHARED_ROOT="$(cd "$COMMON_GIT_DIR/.." && pwd)"
fi

UVICORN_BIN="$ROOT/.venv/bin/uvicorn"
if [ ! -x "$UVICORN_BIN" ] && [ -n "$SHARED_ROOT" ] && [ -x "$SHARED_ROOT/.venv/bin/uvicorn" ]; then
  UVICORN_BIN="$SHARED_ROOT/.venv/bin/uvicorn"
fi
if [ ! -x "$UVICORN_BIN" ]; then
  UVICORN_BIN="$(command -v uvicorn || true)"
fi
if [ -z "$UVICORN_BIN" ] || [ ! -x "$UVICORN_BIN" ]; then
  echo "오류: uvicorn 실행 파일을 찾지 못했습니다. 로컬 .venv 또는 공용 작업공간 .venv 를 확인하세요."
  exit 1
fi

VITE_BIN="$ROOT/frontend/node_modules/.bin/vite"
if [ ! -x "$VITE_BIN" ] && [ -n "$SHARED_ROOT" ] && [ -x "$SHARED_ROOT/frontend/node_modules/.bin/vite" ]; then
  VITE_BIN="$SHARED_ROOT/frontend/node_modules/.bin/vite"
fi
if [ ! -x "$VITE_BIN" ]; then
  echo "오류: vite 실행 파일을 찾지 못했습니다. frontend/node_modules 설치가 필요합니다."
  exit 1
fi

BACKEND_STARTED=0
# 포트가 비어 있으면 백엔드 시작, 이미 떠 있으면 기존 백엔드를 재사용
if command -v lsof >/dev/null 2>&1 && lsof -ti:"$BACKEND_PORT" >/dev/null 2>&1; then
  echo "백엔드 포트 $BACKEND_PORT 사용 중: 기존 백엔드를 재사용합니다."
else
  cleanup() {
    echo ""
    if [ "$BACKEND_STARTED" = "1" ]; then
      echo "종료 중: 백엔드(PID $UVICORN_PID) 프론트는 자동 종료됩니다."
      kill "$UVICORN_PID" 2>/dev/null || true
    else
      echo "종료 중: 프론트는 자동 종료됩니다."
    fi
    exit 0
  }
  trap cleanup INT TERM

  echo "백엔드 시작: http://0.0.0.0:$BACKEND_PORT"
  "$UVICORN_BIN" backend.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
  UVICORN_PID=$!
  BACKEND_STARTED=1
fi

sleep 2
VITE_HOST="${VITE_HOST:-0.0.0.0}"
VITE_PORT="${VITE_PORT:-5173}"
echo "프론트엔드 시작: http://$VITE_HOST:$VITE_PORT"
echo "프론트엔드 API 대상: $VITE_API_BASE"
cd frontend && VITE_API_BASE="$VITE_API_BASE" "$VITE_BIN" --host "$VITE_HOST" --port "$VITE_PORT"
