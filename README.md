# 데일리 인텔리전스 뉴스레터

24시간 이내 IT/AI 정보를 수집·분석·요약·중복 제거 후 마크다운 뉴스레터를 생성하고, 메일 발송 및 웹뷰를 제공하는 자동화 파이프라인입니다. 주간 통합 인사이트 레터, 프롬프트 자가 진화, 자동 git push를 지원합니다.

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

# crawl 타입 소스 사용 시 Playwright 브라우저 설치
.venv/bin/playwright install chromium

# X/Twitter · Reddit 소셜 수집 (선택)
uv tool install twitter-cli    # X 검색. 인증: .env에 TWITTER_AUTH_TOKEN, TWITTER_CT0 설정
uv tool install rdt-cli         # Reddit 검색 (실패 시 JSON API 자동 fallback)
```

## 실행 명령어 가이드

### 1. 파이프라인 CLI (1회 실행)

| 명령어 | 설명 |
|--------|------|
| `.venv/bin/python -m pipeline` | **전일** 날짜로 수집·분석·레터 생성·git push (날짜 생략 시 자동) |
| `.venv/bin/python -m pipeline --date 2025-03-01` | **지정 날짜**로 파이프라인 전체 실행 |
| `.venv/bin/python -m pipeline --date 2025-03-01 --force` | 체크포인트 있어도 **처음부터 재실행** |
| `.venv/bin/python -m pipeline --no-push` | 파이프라인 실행 후 **git push 생략** |
| `.venv/bin/python -m pipeline --evolve` | **프롬프트 진화만** 실행 (모든 대상) |
| `.venv/bin/python -m pipeline --evolve analyze` | **특정 에이전트만** 프롬프트 진화 |
| `.venv/bin/python -m pipeline --weekly` | **주간 통합 인사이트 레터** 생성 (직전 완료 주) |
| `.venv/bin/python -m pipeline --weekly --date 2026-04-12` | **특정 날짜가 포함된 주** 주간 레터 생성 |
| `.venv/bin/python -m pipeline --config-dir config --data-dir data --skills-dir skills` | 설정/데이터/스킬 경로 지정 |

### 2. 백엔드 API (레터 목록·피드백·파이프라인 제어)

```bash
.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

- 발송 내역: `GET /api/letters`, `GET /api/letters/{date}`
- 피드백: `POST /api/feedback`, `GET /api/feedback/types`
- **파이프라인**: `GET /api/pipeline/status?date=`, `POST /api/pipeline/run`, `POST /api/pipeline/run-step`
- **주간 레터**: `GET /api/weekly`, `GET /api/weekly/{week_id}`, `GET /api/weekly/{week_id}/meta`, `POST /api/weekly/run`
- **프롬프트 진화**: `GET /api/evolution/versions/{agent}`, `GET /api/evolution/current/{agent}`, `POST /api/evolution/evolve`, `POST /api/evolution/rollback`

### 3. 프론트엔드 (웹 UI)

```bash
cd frontend && npm install && npm run dev
```

- 프론트: **http://localhost:5173**
- API 연동: `frontend/.env` 에 `VITE_API_BASE=http://localhost:8000` 설정 권장
- **파이프라인 탭**: 날짜 선택 → 전체 실행 / 단계만·단계부터 실행, 진행 상황 폴링
- **주간 리뷰 탭**: 트렌드맵, 카테고리 비중, Top5, 주간 레터 본문

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

- 매일 06:00 일간 파이프라인, 매주 월요일 07:00 주간 레터 자동 실행. 중단: `Ctrl+C`

## 파이프라인 단계

### 일간 (collect → ... → git push)

| 단계 | 설명 |
|------|------|
| collect | RSS, HN, Reddit, X/Twitter, 크롤링 소스 병렬 수집 |
| analyze | 4개 카테고리 분류 + 영향도 산정 (LLM) |
| summarize | 섹션별 요약 (LLM) |
| dedup | 7일 데이터 기반 의미적 중복 제거 |
| letter_generate | 마크다운 뉴스레터 본문 생성 (LLM) |
| card_generate | 카드뉴스 JSON 생성 (LLM) |
| card_backgrounds | 배경 이미지 생성 (Gemini) |
| git push | 산출물 자동 커밋/푸시 |

### 주간 (weekly_collect → ... → git push)

| 단계 | 설명 |
|------|------|
| weekly_collect | 7일분 analyze 체크포인트에서 데이터 수집, 에이전틱 코딩 + 인프라 카테고리 필터링 |
| weekly_analyze | 트렌드맵, Top5, 카테고리 통계, 전주 비교 (LLM) |
| weekly_generate | 주간 레터 마크다운 생성 (LLM) |
| weekly_card | 주간 카드뉴스 JSON 생성 (LLM) |
| git push | 산출물 자동 커밋/푸시 |

## 디렉터리

```
config/
  sources.yaml              수집 소스 (rss, hnrss, reddit_rss, github_blog, crawl, twitter_cli, rdt_cli)
  llm.yaml                  LLM provider·model (단일 모델 지정)
  images.yaml               이미지 생성 설정

data/
  letters/YYYY-MM-DD.md     일간 발행본 마크다운
  cards/YYYY-MM-DD.json     일간 카드뉴스 JSON
  cards/YYYYMMDD.png        카드 배경 이미지
  index/YYYY-MM-DD.json     제목/요약/카테고리 인덱스 (dedup + 주간 분석용)
  weekly/YYYY-Www.md        주간 레터 본문
  weekly/YYYY-Www-meta.json 주간 메타 (트렌드맵, Top5, 카테고리 통계)
  weekly/YYYY-Www-cards.json 주간 카드뉴스
  feedback/YYYY-MM-DD.json  호별 피드백
  checkpoints/YYYY-MM-DD/   단계별 체크포인트 (재시도용)
  prompt_versions/           진화된 프롬프트 버전
  prompt_evolution_log/      진화 메타데이터 (diff, 피드백, 사유)

skills/                      에이전트 스킬 마크다운 (base 프롬프트, 수정 금지)
pipeline/                    파이프라인 엔진 (Python)
backend/                     FastAPI 웹 API
frontend/                    React+Vite 웹 UI
```

**백엔드 데이터 경로**: 서비스 재기동 후에도 발송 내역이 동일한 위치를 보려면 `.env`에 `DATA_DIR`을 두고, **항상 프로젝트 루트에서** 백엔드를 실행하세요. `DATA_DIR`이 없으면 코드 기준 프로젝트 루트의 `data`를 사용합니다. 예: `DATA_DIR=data` (기본값과 동일) 또는 `DATA_DIR=/절대경로/data`

## 주간 통합 인사이트 레터

월~일 7일간의 일간 레터를 분석하여 **에이전틱 코딩 & 프론티어 모델 + GitHub & 인프라 트렌드**에 집중한 주간 메타 분석 레터를 생성한다.

- **범위**: 에이전틱 코딩, GitHub/인프라 2개 카테고리 집중 (산업별 AX, 대한민국 IT 필터링)
- **구조**: 주간 트렌드맵(topic × 요일 매트릭스) → Top5 하이라이트 → 카테고리별 주간 정리 → 다음 주 주목 포인트
- **파이프라인**: `weekly_collect → weekly_analyze → weekly_generate → weekly_card`
- **트리거**: CLI `--weekly`, API `POST /api/weekly/run`, 스케줄러 매주 월요일 07:00
- **UI**: 주간 리뷰 탭에서 트렌드맵 테이블, 카테고리 비중 바, Top5 확인 가능

## X/Twitter · Reddit 소셜 수집

일간 수집에 X(Twitter)와 Reddit 소셜 미디어 검색을 통합하여 에이전트 코딩 트렌드를 실시간 수집한다.

- **X/Twitter**: `twitter-cli` (검색/읽기). `uv tool install twitter-cli` + Cookie 인증
- **Reddit**: `rdt-cli` 우선, 실패 시 Reddit JSON API 자동 fallback. `uv tool install rdt-cli`
- **소스 타입**: `twitter_cli` (검색어 기반), `rdt_cli` (검색 또는 서브레딧)
- CLI 미설치 시 해당 소스만 스킵, 파이프라인은 정상 동작

## 프롬프트 자가 진화

피드백이 축적되면 LLM이 기존 프롬프트를 분석하여 개선 버전을 자동 생성한다.

- **진화 대상**: `analyze` (분류/영향도), `letter_generate` (뉴스레터 작성)
- **트리거**: 관련 피드백 5건 이상 + 마지막 진화 후 3일 경과 시 파이프라인 시작 전 자동 실행
- **안전장치**: 유사도 30% 미만 거부, 길이 5배 초과 거부, 필수 키워드 보존 검증, 3일 쿨다운
- **롤백**: `POST /api/evolution/rollback` 또는 이전 버전 자동 복원
- **원본 보존**: `skills/*.md`는 base로 보존, `data/prompt_versions/`에 진화 버전 관리

### 피드백 유형 (7종)

| 유형 | 설명 | 영향 |
|------|------|------|
| wrong_source | 잘못된 대상 수집 | analyze, letter_generate |
| stale | 오래된 정보 | analyze |
| missing_trend | 누락된 트렌드 | analyze, letter_generate |
| add_source | 추가할 소스 | sources.yaml 수동 편집 |
| tone | 어조/톤 문제 | letter_generate |
| structure | 구조/배치 문제 | letter_generate |
| quality | 품질/정확도 문제 | letter_generate |

## 자동 Git Push

파이프라인 완료 후 산출물(`data/` 하위)을 자동으로 git commit & push 한다.

- **커밋 메시지**: `M/D` 형식 (예: `4/12`)
- **대상**: letters, cards, index, weekly, checkpoints, feedback, prompt_versions
- **생략**: `--no-push` 옵션
- push 실패 시 파이프라인 자체는 성공으로 처리

## 테스트

```bash
.venv/bin/pytest tests/ --ignore=tests/test_run_status.py -v
```
