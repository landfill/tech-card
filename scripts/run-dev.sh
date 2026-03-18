#!/usr/bin/env bash
# 백엔드(uvicorn) + 프론트엔드(vite) 한 번에 실행. 종료 시 Ctrl+C 로 둘 다 정리됨.
set -e
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

BACKEND_PORT="${BACKEND_PORT:-8000}"

# 포트 사용 중이면 안내 후 종료 (데이터가 안 보이는 원인 방지)
if command -v lsof >/dev/null 2>&1; then
  if lsof -ti:"$BACKEND_PORT" >/dev/null 2>&1; then
    echo "오류: 포트 $BACKEND_PORT 이(가) 이미 사용 중입니다. 백엔드가 떠 있지 않으면 발송 내역이 보이지 않습니다."
    echo "기존 프로세스를 종료하려면: lsof -ti:$BACKEND_PORT | xargs kill -9"
    echo "또는 다른 포트로 실행: BACKEND_PORT=8001 ./scripts/run-dev.sh"
    exit 1
  fi
fi

cleanup() {
  echo ""
  echo "종료 중: 백엔드(PID $UVICORN_PID) 프론트는 자동 종료됩니다."
  kill "$UVICORN_PID" 2>/dev/null || true
  exit 0
}
trap cleanup INT TERM

echo "백엔드 시작: http://0.0.0.0:$BACKEND_PORT"
.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port "$BACKEND_PORT" &
UVICORN_PID=$!

sleep 2
echo "프론트엔드 시작: http://localhost:5173"
cd frontend && npm run dev
