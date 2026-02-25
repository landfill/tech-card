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
```

## 실행

### 파이프라인 1회 실행

```bash
.venv/bin/python -m pipeline run --date 2025-02-26
# 옵션: --config-dir config --data-dir data --skills-dir skills --force
```

### 백엔드 API (발송 내역·피드백)

```bash
.venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 프론트엔드

```bash
cd frontend && npm install && npm run dev
# 프론트는 http://localhost:5173, API는 http://localhost:8000. frontend/.env에 VITE_API_BASE=http://localhost:8000 설정 권장.
```

### 일일 스케줄 (로컬)

```bash
.venv/bin/python scripts/scheduler.py
# 매일 06:00에 파이프라인 실행. 중단하려면 Ctrl+C.
```

## 디렉터리

- `config/sources.yaml` — 수집 소스 (RSS, hnrss, reddit_rss, github_blog 등)
- `config/llm.yaml` — LLM provider·model (단일 모델 지정)
- `data/letters/` — 발행본 마크다운 (YYYY-MM-DD.md)
- `data/feedback/` — 호별 피드백
- `data/checkpoints/` — 단계별 체크포인트 (재시도용)
- `skills/` — 에이전트 스킬 마크다운

## 테스트

```bash
.venv/bin/pytest tests/ -v
```
