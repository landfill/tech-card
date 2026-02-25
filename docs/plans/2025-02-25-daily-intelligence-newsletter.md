# 데일리 인텔리전스 뉴스레터 — 구현 계획

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 수집→분석→요약→중복제거→레터생성→발행 파이프라인과 발송 내역 웹뷰·피드백 폼을 갖춘 데일리 뉴스레터 자동화 시스템을 구현한다.

**Architecture:** 독립 A2A 러너가 agents/skills/tools(파일 기반)를 사용해 단계별로 실행. 수집은 소스 단위 병렬, 체크포인트로 중단점 재개. 백엔드는 FastAPI(JSON API), 프론트는 React/Vite. LLM은 설정으로 지정한 단일 모델만 사용하며, 모델별 어댑터(엔드포인트·페이로드·프롬프팅)가 설정에 따라 로드된다.

**Tech Stack:** Python 3.11+ (pipeline, backend, tools), FastAPI, React+Vite, PyYAML, feedparser, httpx, APScheduler. 참고 설계: `docs/plans/2025-02-25-daily-intelligence-newsletter-design.md`

---

## Phase 1: 프로젝트 골격·설정

### Task 1.1: 디렉터리 및 의존성 파일 생성

**Files:**
- Create: `pyproject.toml` (또는 `requirements.txt`)
- Create: `config/sources.yaml`, `config/llm.yaml.example`, `.env.example`
- Create: `data/.gitkeep`, `data/letters/.gitkeep`, `data/index/.gitkeep`, `data/feedback/.gitkeep`, `data/checkpoints/.gitkeep`, `data/subscribers.json`

**Step 1:** 프로젝트 루트에 `pyproject.toml` 생성 (또는 `requirements.txt`).

```toml
[project]
name = "daily-intelligence-newsletter"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.32",
  "pyyaml>=6.0",
  "httpx>=0.27",
  "feedparser>=6.0",
  "apscheduler>=3.10",
  "pydantic>=2.0",
  "pydantic-settings>=2.0",
]
```

**Step 2:** `config/sources.yaml` 생성 — 소스 스키마 예시 2건 (rss, github).

```yaml
sources:
  - id: example-rss
    type: rss
    url: https://example.com/feed.xml
    enabled: true
  - id: example-github
    type: github
    repo: owner/repo
    enabled: true
```

**Step 3:** `config/llm.yaml.example` 생성.

```yaml
# 사용할 모델 하나만 지정. 폴백 없음.
provider: google   # google | openai
model: gemini-3-flash-preview
# api_key, base_url 등은 .env에서 주입
```

**Step 4:** `.env.example` 생성 (API 키 플레이스홀더).

```
GOOGLE_API_KEY=
OPENAI_API_KEY=
DATA_DIR=data
```

**Step 5:** `data/` 하위 디렉터리 및 `data/subscribers.json` 생성. 빈 디렉터리는 `.gitkeep`으로 유지.

```json
[]
```
→ `data/subscribers.json` 내용은 빈 배열 `[]`.

**Step 6:** Commit

```bash
git add pyproject.toml config/ .env.example data/
git commit -m "chore: 프로젝트 골격 및 설정 파일 추가"
```

---

### Task 1.2: 소스 설정 로더 및 검증

**Files:**
- Create: `pipeline/config.py`
- Create: `tests/test_config.py`

**Step 1:** `tests/test_config.py`에 실패할 테스트 작성 — `load_sources()`가 `config/sources.yaml`에서 리스트를 반환하고, `enabled: true`만 필터링.

**Step 2:** `pytest tests/test_config.py -v` 실행 → 실패 확인.

**Step 3:** `pipeline/config.py`에 `load_sources(path) -> list[dict]` 구현. PyYAML로 로드 후 `sources` 키에서 `enabled`가 True인 항목만 반환.

**Step 4:** `pytest tests/test_config.py -v` 실행 → 통과 확인.

**Step 5:** Commit

```bash
git add pipeline/config.py tests/test_config.py
git commit -m "feat: 소스 설정 로더 및 enabled 필터"
```

---

## Phase 2: 데이터 레이어

### Task 2.1: 체크포인트 읽기/쓰기

**Files:**
- Create: `pipeline/checkpoint.py`
- Create: `tests/test_checkpoint.py`

**Step 1:** `tests/test_checkpoint.py` — `save_checkpoint(date, stage, payload)`, `load_checkpoint(date, stage)`, `list_completed_stages(date)` 테스트. 임시 디렉터리 사용.

**Step 2:** pytest 실행 → 실패.

**Step 3:** `pipeline/checkpoint.py` 구현. 경로 `data/checkpoints/YYYY-MM-DD/<stage>.json`, JSON 직렬화.

**Step 4:** pytest 통과 확인.

**Step 5:** Commit `feat: 체크포인트 저장/로드`

---

### Task 2.2: 7일 인덱스 및 레터 경로 유틸

**Files:**
- Create: `pipeline/storage.py`
- Create: `tests/test_storage.py`

**Step 1:** 테스트 — `letter_path(date)` → `data/letters/YYYY-MM-DD.md`, `index_path(date)` → `data/index/YYYY-MM-DD.json`, `recent_7d_dates(date)` → 당일 기준 과거 7일 날짜 리스트.

**Step 2:** 구현 후 pytest 통과, Commit `feat: 레터/인덱스 경로 및 7일 날짜 유틸`

---

### Task 2.3: 피드백 저장/로드

**Files:**
- Create: `pipeline/feedback_store.py`
- Modify: `backend/` 또는 `api/` (아직 없으면 Task 2.3에서 `pipeline/feedback_store.py`만 생성)

**Step 1:** `pipeline/feedback_store.py` — `save_feedback(issue_date, feedback_type, content)`, `load_feedback_since(cutoff_date)` (또는 `load_feedback_for_run()`). 저장 경로 `data/feedback/YYYY-MM-DD.json` (호별) 또는 단일 파일. 스키마: `{ "issue_date": "YYYY-MM-DD", "type": "...", "content": "...", "created_at": "ISO8601" }`.

**Step 2:** 테스트 `tests/test_feedback_store.py` 작성 및 통과, Commit `feat: 피드백 저장/로드`

---

## Phase 3: LLM 클라이언트 (설정 기반·모델별 어댑터)

### Task 3.1: 설정 로드 및 어댑터 선택

**Files:**
- Create: `pipeline/llm/__init__.py`
- Create: `pipeline/llm/config.py` — `config/llm.yaml` + env에서 provider/model 로드, 검증
- Create: `pipeline/llm/base.py` — 공통 인터페이스 `LLMAdapter.generate(system: str, user: str) -> str` (ABC 또는 Protocol)
- Create: `tests/test_llm_config.py`

**Step 1:** `config/llm.yaml`을 읽어 `provider`, `model` 반환. env에서 해당 provider의 API 키 주입. 테스트는 fixture yaml로 provider/google, model/gemini-3-flash-preview 검증.

**Step 2:** Commit `feat: LLM 설정 로드 (단일 모델 지정)`

---

### Task 3.2: Gemini 어댑터

**Files:**
- Create: `pipeline/llm/adapters/gemini.py`
- Create: `tests/test_llm_gemini.py` (mock 또는 skip if no key)

**Step 1:** `LLMAdapter` 구현. Google API 엔드포인트·페이로드 형식(시스템/유저 메시지 구조)에 맞춰 요청. 응답 파싱 후 텍스트 반환. 모델별 프롬프팅 규칙(예: role 필드명, 메시지 배열 형태)은 이 모듈에만 두고, 공통 인터페이스는 `generate(system, user) -> str`.

**Step 2:** 테스트에서 mock 응답으로 반환 문자열 검증. Commit `feat: Gemini LLM 어댑터`

---

### Task 3.3: OpenAI 어댑터

**Files:**
- Create: `pipeline/llm/adapters/openai.py`
- Create: `tests/test_llm_openai.py` (mock 또는 skip if no key)

**Step 1:** `LLMAdapter` 구현. OpenAI API 엔드포인트·페이로드(메시지 형식, 모델 필드)에 맞춰 요청. 응답 파싱 후 텍스트 반환. 프롬프팅 규칙은 OpenAI 문서 기준으로 이 모듈에만 정의.

**Step 2:** 테스트에서 mock 응답 검증. Commit `feat: OpenAI LLM 어댑터`

---

### Task 3.4: 설정에 따른 어댑터 인스턴스 생성

**Files:**
- Create: `pipeline/llm/client.py` (또는 `pipeline/llm/__init__.py`에서 export)
- Modify: `pipeline/llm/config.py` (이미 있음)

**Step 1:** `get_llm_client(config_path, env)` — config 로드 후 `provider` 값에 따라 `adapters.gemini` 또는 `adapters.openai` 인스턴스 생성해 반환. 한 번만 생성해 재사용하거나, 호출 시마다 생성하도록 결정. 설정에 없는 provider면 명시적 에러.

**Step 2:** 파이프라인/에이전트에서 `get_llm_client()`로 클라이언트를 받아 `generate()`만 호출하도록 사용처는 동일 인터페이스만 의존. Commit `feat: 설정 기반 LLM 어댑터 선택`

---

## Phase 4: 툴 (수집)

### Task 4.1: RSS 수집 툴

**Files:**
- Create: `tools/fetch_rss.py` (CLI 또는 `def fetch(url: str) -> list[dict]`)
- Create: `tests/test_fetch_rss.py`

**Step 1:** 테스트 — `fetch_rss(url)`가 항목 리스트 반환 (제목, 링크, 요약, 시각 등). 실제 공개 RSS로 한 건 호출하거나 fixture.

**Step 2:** `tools/fetch_rss.py` — feedparser 사용, 공통 스키마 `{ "title", "url", "summary", "published" }` 반환.

**Step 3:** pytest 통과, Commit `feat: RSS 수집 툴`

---

### Task 4.2: GitHub 트렌드 툴 (스텁 또는 API)

**Files:**
- Create: `tools/fetch_github.py`
- Create: `tests/test_fetch_github.py`

**Step 1:** `fetch_github_trending()` 또는 `fetch_repo(repo)` — GitHub REST API로 리포 정보/트렌드 대체 데이터 반환. 테스트는 mock 또는 공개 API 호출.

**Step 2:** 구현 및 통과, Commit `feat: GitHub 수집 툴`

---

### Task 4.3: 수집 오케스트레이션 (소스별 병렬)

**Files:**
- Create: `pipeline/collect.py`
- Create: `tests/test_collect.py`

**Step 1:** `run_collect(date, sources_config_path, output_path)` — `config.load_sources()` 호출 후 type별로 `tools/fetch_rss`, `tools/fetch_github` 등 호출. `concurrent.futures.ThreadPoolExecutor`로 병렬. 한 소스 예외 시 로그 후 스킵, 나머지 결과 병합해 JSON으로 저장. 저장 위치는 체크포인트 또는 `data/checkpoints/YYYY-MM-DD/collect.json`.

**Step 2:** 테스트에서 소스 2개 stub으로 병렬 호출·결과 병합 검증.

**Step 3:** Commit `feat: 수집 단계 병렬 실행`

---

## Phase 5: 스킬·에이전트 (분석·요약·중복제거·레터생성)

### Task 5.1: 스킬 파일 생성

**Files:**
- Create: `skills/collect.md`, `skills/analyze.md`, `skills/summarize.md`, `skills/dedup.md`, `skills/letter_generate.md`, `skills/publish.md`

**Step 1:** 각 파일에 frontmatter + 짧은 지시문. 예:

```markdown
---
name: analyze
description: 수집 결과를 도메인별로 분류하고 핵심 이슈 추출
---
# Analyze
수집된 raw 항목을 다음 카테고리로 분류하라: 에이전틱 코딩, GitHub·인프라, 트래블 AX, 한국 IT. 각 항목에 제목, 요약, 출처, 영향도(high/medium/low)를 부여하라.
```

**Step 2:** Commit `feat: 에이전트 스킬 마크다운 6종`

---

### Task 5.2: 분석·요약 에이전트 러너

**Files:**
- Create: `pipeline/agents.py` (또는 `pipeline/run_agent.py`)
- Create: `tests/test_agents.py`

**Step 1:** `run_agent(agent_name, input_payload, skills_dir, llm_client)` — `skills/<agent_name>.md` 읽어서 system 프롬프트로 사용, input_payload를 JSON으로 user 메시지에 넣고 LLM 호출, 응답 파싱(JSON 또는 텍스트) 반환.

**Step 2:** 테스트 — analyze 에이전트에 더미 수집 결과 넣고 실행 (mock LLM 또는 skip if no key).

**Step 3:** Commit `feat: 스킬 기반 에이전트 러너`

---

### Task 5.3: 중복 제거 (임베딩 + LLM)

**Files:**
- Create: `pipeline/dedup.py`
- Create: `tests/test_dedup.py`

**Step 1:** `dedup(candidates, recent_7d_items, llm_client, threshold)` — recent_7d_items와 candidates를 임베딩 비교(간단한 텍스트 유사도 또는 외부 임베딩 API). 임계값 넘는 항목을 LLM에 “지난 7일과 실질 동일한가?” 질의해 제외/포함 결정. 테스트는 고정 입력으로 제외된 항목 수 검증.

**Step 2:** 구현 (임베딩은 Gemini embedding 또는 간단 해시/키워드 오버랩으로 1차 구현 가능).

**Step 3:** Commit `feat: 의미적 중복 제거 (임베딩+LLM)`

---

### Task 5.4: 레터 생성 에이전트

**Files:**
- Modify: `skills/letter_generate.md` (이미 있음)
- Create: `pipeline/letter_generate.py`

**Step 1:** `letter_generate(analyzed_and_deduped_payload, skill_path)` — 스킬 내용 + payload로 LLM 호출, 마크다운 본문 문자열 반환. 출력을 `data/letters/YYYY-MM-DD.md`에 저장하는 것은 파이프라인 러너에서 수행.

**Step 2:** 테스트에서 더미 payload로 마크다운 문자열 반환 검증.

**Step 3:** Commit `feat: 레터 생성 에이전트`

---

## Phase 6: 파이프라인 러너

### Task 6.1: 단계 순서 및 체크포인트 연동

**Files:**
- Create: `pipeline/runner.py`
- Create: `tests/test_runner.py`

**Step 1:** `run_pipeline(date, config_dir, data_dir)` — 단계: collect → analyze → summarize → dedup → letter_generate. 각 단계 전에 `load_checkpoint(date, stage)` 존재하면 스킵(또는 옵션으로 덮어쓰기). 단계 후 `save_checkpoint(date, stage, result)`. letter_generate 결과를 `storage.letter_path(date)`에 저장.

**Step 2:** 테스트 — mock 단계들, 체크포인트 디렉터리 사용, 한 단계 실패 시 재실행 시 이전 단계 스킵 검증.

**Step 3:** Commit `feat: 파이프라인 러너 및 체크포인트 연동`

---

### Task 6.2: CLI 진입점

**Files:**
- Create: `pipeline/__main__.py` 또는 `scripts/run_pipeline.py`

**Step 1:** `python -m pipeline run` 또는 `python scripts/run_pipeline.py --date YYYY-MM-DD`. `--date` 없으면 오늘. `run_pipeline(date, ...)` 호출.

**Step 2:** 수동 실행으로 동작 확인.

**Step 3:** Commit `feat: 파이프라인 CLI 진입점`

---

### Task 6.3: 발행 단계 (메일 발송 스텁)

**Files:**
- Create: `tools/send_email.py`
- Create: `pipeline/publish.py`

**Step 1:** `send_email(to_list, subject, body_md)` — SMTP 또는 SendGrid 등 연동. 1차는 로그만 출력하는 스텁으로 구현 가능. `publish.py`는 `letter_path(date)` 읽어서 HTML 변환 또는 plain text로 발송.

**Step 2:** 수신자 목록은 `data/subscribers.json`에서 로드.

**Step 3:** Commit `feat: 발행 단계 및 메일 발송 (스텁 또는 SMTP)`

---

## Phase 7: 백엔드 API

### Task 7.1: FastAPI 앱 및 발송 내역 API

**Files:**
- Create: `backend/main.py` (또는 `api/main.py`)
- Create: `backend/routers/letters.py`

**Step 1:** FastAPI 앱 생성. `GET /api/letters` — `data/letters/` 목록 (날짜순). `GET /api/letters/{date}` — 해당 날짜 마크다운 본문 반환 (또는 파일 서빙).

**Step 2:** `GET /api/letters/by-weekday` — 요일별 그룹 (선택). uvicorn으로 기동 확인.

**Step 3:** Commit `feat: 발송 내역 API`

---

### Task 7.2: 피드백 제출 API

**Files:**
- Create: `backend/routers/feedback.py`

**Step 1:** `POST /api/feedback` — body `{ "issue_date": "YYYY-MM-DD", "type": "wrong_source|stale|missing_trend|add_source", "content": "..." }`. `pipeline/feedback_store.save_feedback()` 호출.

**Step 2:** Commit `feat: 피드백 제출 API`

---

## Phase 8: 프론트엔드

### Task 8.1: React+Vite 프로젝트 생성

**Files:**
- Create: `frontend/` (npm create vite@latest frontend -- --template react-ts 또는 react)

**Step 1:** Vite + React 프로젝트 생성. `frontend/.env`에 `VITE_API_BASE=http://localhost:8000` (백엔드 주소).

**Step 2:** Commit `chore: React+Vite 프론트엔드 초기화`

---

### Task 8.2: 발송 내역 목록·요일별 뷰

**Files:**
- Create: `frontend/src/pages/LetterList.tsx` (또는 .jsx)
- Create: `frontend/src/pages/LetterDetail.tsx`
- Modify: `frontend/src/App.tsx`

**Step 1:** `GET /api/letters` 호출해 목록 표시. 날짜 클릭 시 `GET /api/letters/{date}`로 상세. 상세 페이지에서 마크다운 렌더 (react-markdown 등).

**Step 2:** 요일별 그룹 탭 또는 필터 (선택).

**Step 3:** Commit `feat: 발송 내역 목록 및 상세 뷰`

---

### Task 8.3: 피드백 폼

**Files:**
- Create: `frontend/src/components/FeedbackForm.tsx`
- Modify: `frontend/src/pages/LetterDetail.tsx`

**Step 1:** 상세 페이지에 “이 호에 대한 피드백” 폼. 필드: 유형(드롭다운), 내용(텍스트). `POST /api/feedback` 호출. issue_date는 현재 보고 있는 레터 날짜.

**Step 2:** 제출 후 성공 메시지 표시.

**Step 3:** Commit `feat: 호별 피드백 폼`

---

## Phase 9: 스케줄러 및 피드백 주입

### Task 9.1: APScheduler로 매일 파이프라인 실행

**Files:**
- Create: `pipeline/scheduler.py` 또는 `scripts/scheduler.py`

**Step 1:** APScheduler로 CronTrigger 매일 06:00 (또는 설정 가능). job에서 `run_pipeline(today)` 호출. 단일 프로세스로 실행.

**Step 2:** `python -m pipeline.scheduler` 또는 `python scripts/scheduler.py`로 기동 확인 (테스트 시 트리거 시간 짧게 조정 가능).

**Step 3:** Commit `feat: APScheduler 일일 파이프라인 실행`

---

### Task 9.2: 수집/분석 시 피드백 컨텍스트 주입

**Files:**
- Modify: `pipeline/collect.py` 또는 `pipeline/agents.py`
- Modify: `pipeline/feedback_store.py` (이미 있음)

**Step 1:** 파이프라인 실행 시 `load_feedback_since(cutoff_date)` 호출 (예: 최근 7일). 수집/분석 에이전트의 system 프롬프트 뒤에 “최근 피드백: …” 문자열 append.

**Step 2:** 테스트에서 피드백이 있을 때 프롬프트에 포함되는지 검증 (mock).

**Step 3:** Commit `feat: 파이프라인에 피드백 컨텍스트 주입`

---

## Phase 10: 정리·문서

### Task 10.1: README 및 실행 방법

**Files:**
- Create: `README.md`

**Step 1:** README에 프로젝트 개요, 설계 문서 링크, 로컬 실행 방법 (설치, `.env` 설정, `python -m pipeline run`, 백엔드/프론트 기동, 스케줄러 기동).

**Step 2:** Commit `docs: README 및 실행 가이드`

---

## 실행 옵션

계획 저장 완료: `docs/plans/2025-02-25-daily-intelligence-newsletter.md`

### 방식 1: Subagent-Driven (이 세션)

- **방법**: 지금 대화에서 태스크(Phase 1.1, 1.2, 2.1 …)마다 서브에이전트를 한 번씩 호출. 각 태스크 완료 후 여기서 결과를 검토하고 다음 태스크로 진행.
- **장점**: 한 세션 안에서 진행·수정·리뷰가 이어져, 꼬인 부분을 바로 잡기 좋음. “이 태스크만 다시” 같은 세밀한 제어 가능.
- **단점**: 태스크 수가 많아서 대화가 길어지고, 중간에 끊기면 이어받기가 다소 번거로울 수 있음.

### 방식 2: 별도 세션 (Executing-Plans)

- **방법**: 새 채팅을 열고, 구현 계획 문서를 열어둔 뒤 **executing-plans** 스킬을 사용. “이 계획대로 Phase 1부터 순서대로 실행해줘”라고 요청. 계획에 있는 체크포인트(Phase/태스크 단위)마다 멈추고 검토한 뒤 다음 배치 실행.
- **장점**: 구현 전용 세션이라 계획만 보고 배치로 진행 가능. 체크포인트로 구간별 검증이 명확함.
- **단점**: 지금 대화 맥락(설계 논의, 선택한 옵션 등)이 새 세션에 없으므로, 필요하면 “설계 문서·구현 계획 경로”와 “설정 기반 LLM, 모델별 어댑터” 같은 요약을 한 줄 넣어주는 것이 좋음.

---

### 추천: **방식 1 (Subagent-Driven, 이 세션)**

- 지금까지 설계·계획을 이 대화에서 같이 맞춰왔기 때문에, **Phase 1~2(골격·설정·데이터 레이어)** 는 이 세션에서 Subagent-Driven으로 진행하는 것을 추천합니다.
- 초기 구조와 설정이 잡힌 뒤에는, 원하시면 **Phase 7~8(백엔드·프론트)** 부터는 새 세션에서 executing-plans로 배치 실행하는 식으로 나누어도 됩니다.

**정리**: 우선 **방식 1**로 Phase 1부터 진행하고, 중간에 “이제부터는 새 세션에서 계획만 보고 돌려줘”로 전환하는 흐름을 추천합니다.

원하시는 방식을 알려주시면 그에 맞춰 진행하겠습니다.
