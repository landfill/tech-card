# 데일리 인텔리전스 뉴스레터

24시간 이내 IT/AI 정보를 수집·분석·요약·중복 제거 후 마크다운 뉴스레터를 생성하고, 메일 발송 및 웹뷰를 제공하는 자동화 파이프라인입니다.

## 설계·계획

- [설계 문서](docs/plans/2025-02-25-daily-intelligence-newsletter-design.md)
- [구현 계획](docs/plans/2025-02-25-daily-intelligence-newsletter.md)
- [수집 전략 (비 API)](docs/sources-non-api-strategy.md)

## 요구사항

- Python 3.11+
- Node 18+ (프론트엔드 개발 시)

## 설치

```bash
python -m venv .venv
.venv/bin/pip install -e .
cp config/llm.yaml.example config/llm.yaml
# config/llm.yaml에 사용할 provider·model 설정. .env에 GOOGLE_API_KEY 또는 OPENAI_API_KEY 설정

# crawl 타입 소스 사용 시 Playwright 브라우저 설치 (단일 방식, 수집 소스 병렬: 브라우저 1개·다중 페이지)
.venv/bin/playwright install chromium
```

## 실행 명령어 가이드

### 1. 파이프라인 CLI (1회 실행)

| 명령어 | 설명 |
|--------|------|
| `.venv/bin/python -m pipeline` | **전일** 날짜로 수집·분석·레터 생성 (날짜 생략 시 자동) |
| `.venv/bin/python -m pipeline --date 2025-03-01` | **지정 날짜**로 파이프라인 전체 실행 |
| `.venv/bin/python -m pipeline --date 2025-03-01 --force` | 체크포인트 있어도 **처음부터 재실행** |
| `.venv/bin/python -m pipeline --config-dir config --data-dir data --skills-dir skills` | 설정/데이터/스킬 경로 지정 |

### 2. 백엔드 API (레터 목록·피드백·파이프라인 제어)

```bash
.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- 발송 내역: `GET /api/letters`, `GET /api/letters/{date}`
- 피드백: `POST /api/feedback`
- **파이프라인**: `GET /api/pipeline/status?date=`, `POST /api/pipeline/run`, `POST /api/pipeline/run-step`

### 3. 프론트엔드 (웹 UI)

```bash
cd frontend && npm install && npm run dev
```

- 프론트: **http://localhost:5173**
- API 연동: `frontend/.env` 에 `VITE_API_BASE=http://localhost:8000` 설정 권장
- **파이프라인 탭**: 날짜 선택 → 전체 실행 / 단계만·단계부터 실행, 진행 상황 폴링

### 4. 백엔드 + 프론트 한 번에 실행

**방법 A: 스크립트 (한 터미널)**

```bash
# 최초 1회: frontend 의존성 설치
cd frontend && npm install && cd ..

# 백엔드(8000) + 프론트(5173) 동시 실행. 종료: Ctrl+C
chmod +x scripts/run-dev.sh
./scripts/run-dev.sh
```

- 백엔드: **http://localhost:8000**
- 프론트: **http://localhost:5173**
- 포트 변경: `BACKEND_PORT=9000 ./scripts/run-dev.sh`

**방법 B: 터미널 두 개**

| 터미널 1 (백엔드) | 터미널 2 (프론트) |
|------------------|------------------|
| `.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000` | `cd frontend && npm run dev` |

### 5. 파이프라인 UI로 실행 (권장)

1. 위 **4번**으로 백엔드+프론트 실행 (스크립트 또는 터미널 2개)
2. 브라우저 **http://localhost:5173** → **파이프라인** 탭 → 날짜 선택 후 **전체 실행** 또는 단계별 실행

### 6. 일일 스케줄 (로컬)

```bash
.venv/bin/python scripts/scheduler.py
```

- 매일 06:00에 파이프라인 자동 실행. 중단: `Ctrl+C`

## 디렉터리

- `config/sources.yaml` — 수집 소스 (RSS, hnrss, reddit_rss, github_blog, crawl 등)
- `config/llm.yaml` — LLM provider·model (단일 모델 지정)
- `data/letters/` — 발행본 마크다운 (YYYY-MM-DD.md)
- `data/feedback/` — 호별 피드백
- `data/checkpoints/` — 단계별 체크포인트 (재시도용)
- `skills/` — 에이전트 스킬 마크다운

**백엔드 데이터 경로**: 서비스 재기동 후에도 발송 내역이 동일한 위치를 보려면 `.env`에 `DATA_DIR`을 두고, **항상 프로젝트 루트에서** 백엔드를 실행하세요. `DATA_DIR`이 없으면 코드 기준 프로젝트 루트의 `data`를 사용합니다. 예: `DATA_DIR=data` (기본값과 동일) 또는 `DATA_DIR=/절대경로/data`

## 테스트

```bash
.venv/bin/pytest tests/ -v
```
