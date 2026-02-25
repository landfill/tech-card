# 데일리 인텔리전스 뉴스레터 — 설계 문서

**문서 일자**: 2025-02-25  
**상태**: 설계 확정

---

## 1. 목표·범위

- 24시간 이내 최신 IT/AI 정보를 분석해, 보도자료 노이즈를 줄이고 개발자·산업 실무자에게 즉시 쓸 수 있는 통찰을 주는 **데일리 인텔리전스 뉴스레터** 자동 생성·발행.
- **워크플로**: 수집 → 분석 → 요약 → (7일 데이터 기반 의미적 중복 제거) → 레터 생성 → 발행(메일 + 요일별 발송 내역 웹뷰).
- **저장**: 발행본 마크다운 일자별 저장 → 다음 호 생성 시 과거 데이터로 중복 제거.
- **피드백**: 웹 UI에서 호별 피드백 제출 → 저장 → 다음 수집/분석/요약 프롬프트(가능하면 스킬 MD)에 반영.

---

## 2. 아키텍처 개요

- **오케스트레이터**: 단일 파이프라인 러너(CLI `run`). 각 단계를 에이전트로 실행하고, 단계 간 컨텍스트는 구조화된 payload(JSON)로 전달.
- **에이전트 체인**: Collector → Analyzer → Summarizer → Dedup → LetterGenerator → Publisher. 각 에이전트는 `skills/`의 SKILL.md + `tools/`의 bash/py를 사용.
- **스케줄링**: 로컬에서는 APScheduler(또는 동일 repo의 스케줄 워커)가 매일 지정 시각에 파이프라인 CLI 실행. 클라우드 전환 시에는 같은 CLI를 VM/cron 또는 HTTP 트리거로만 호출하도록 설정만 변경.
- **웹**: FastAPI(JSON API) + React/Vite. 발송 내역·요일별 뷰·호별 피드백 폼. 접근 제어 없음, 기본 localhost.

---

## 3. 병렬 실행

- **원칙**: 의존성이 없는 에이전트/프로세스는 **병렬 실행**하도록 설계한다.
- **수집(Collect)**  
  - 소스별로 독립이므로 **소스 단위 병렬** 실행.  
  - `config/sources.yaml`에 정의된 각 소스에 대해 동시에 수집 툴 호출(스레드 풀 또는 비동기). 소스 하나 실패 시 해당 소스만 스킵하고 나머지 결과만 합쳐서 다음 단계로 전달.
- **분석·요약**  
  - 카테고리/채널별로 나눌 수 있으면(예: “에이전틱 코딩” / “GitHub 트렌드” / “트래블 AX” 등) **카테고리 단위 병렬** 검토. 공통 컨텍스트가 크면 순차로 두고, 독립 블록이면 병렬.
- **기타**  
  - Dedup, LetterGenerate, Publish는 이전 단계 결과에 의존하므로 순차.  
  - 러너는 병렬 가능한 단계에서만 `concurrent.futures` 또는 asyncio 등으로 병렬 실행하고, 단계 간에는 순서를 보장.

---

## 4. 수집 소스 관리

- **대상**: X, Threads, Reddit, Claude/OpenAI 등 프론티어 공식 블로그, 기타 AI 상위 커뮤니티, GitHub.
- **관리 방식**  
  - **파일 기반 설정**으로 추가·제거. UI는 필수가 아님.  
  - 예: `config/sources.yaml`(또는 `config/sources.json`)에 소스 목록을 두고, 항목 추가/삭제/비활성화(예: `enabled: false`)로 관리.  
  - 스키마 예: `id`, `type`(rss|github|x|threads|reddit|blog 등), `url` 또는 `account`/`query`, `enabled`, 필요 시 `options`.  
- **동작**: 파이프라인 실행 시 설정 파일을 한 번 읽어, `enabled`인 소스만 수집 대상으로 사용. 수집 단계는 이 목록을 기준으로 병렬 실행.  
- **수작업**: 소스 추가·제거·수정은 `config/sources.yaml` 편집으로 수행 가능. (추후 소스 관리 UI를 넣을 경우 같은 스키마를 API로 읽고 쓸 수 있도록 설계.)

---

## 5. 데이터·저장소

- **저장 방식**: 파일 기반. 발행본 본문은 **마크다운**으로 저장.
- **경로 규칙**
  - 발행본: `data/letters/YYYY-MM-DD.md`
  - 7일 제목·키워드 인덱스(중복 제거용): `data/index/recent-7d.json` 또는 일자별 `data/index/YYYY-MM-DD.json` 갱신 후 파이프라인이 최근 7일분 병합해 사용
  - 피드백: `data/feedback/YYYY-MM-DD.json`(호별) 또는 단일 `data/feedback.json`에 issue_id·타입·내용·시각 append
  - 수신자 목록: `data/subscribers.json` (이메일 목록 등)
- **체크포인트(재시도)**: 각 단계 완료 시 해당 단계 출력을 `data/checkpoints/YYYY-MM-DD/<stage>.json`에 저장. 워크플로 중단 시 마지막 성공 단계부터 재실행 가능.

---

## 6. 수집 레이어·하이브리드

- **구현**: 봇 차단·성능을 위해 하이브리드.
  - RSS/공식 블로그: Python requests/feedparser 또는 전용 툴.
  - X / Threads / Reddit: Playwright(브라우저) 또는 API를 툴로 래핑. 필요 시 Node 스크립트를 툴에서 호출.
  - GitHub: REST API를 Python 툴로 호출.
- **소스 목록**: `config/sources.yaml`에서 읽어 순회. 소스 추가/제거는 이 파일 수정으로만 해도 반영되도록 설계(수집 소스 관리 참고).

---

## 7. 파이프라인 단계·에러·재시도

- **단계 순서**: Collect(병렬) → Analyze(병렬 가능 시) → Summarize(병렬 가능 시) → Dedup → LetterGenerate → Publish. 단계 간에는 순차.
- **에러**: 부분 진행. 한 소스 수집 실패 시 해당 소스만 스킵. 단계 전체 실패 시 그 단계에서 중단.
- **재시도**: 워크플로 중단 시 중단점부터 재시도. 체크포인트를 읽어 마지막 성공 단계 다음부터 실행. 같은 날 재실행 시 이미 완료된 단계는 체크포인트가 있으면 스킵(또는 옵션으로 덮어쓰기).
- **알림**: 실패 시 알림 없음. 로그만 남김.

---

## 8. 중복 제거

- **의미적 중복**: 임베딩 유사도 + LLM 판정 조합.
  - 지난 7일 제목·요약(또는 키워드)을 임베딩으로 저장해 두고, 후보 항목과 유사도(코사인) 계산. 임계값 넘으면 “의심 후보”.
  - 의심 후보에 대해 LLM(**gemini-3-flash-preview**)으로 “지난 7일 다룬 내용과 실질적으로 같은가? 새로운 진화·차별점이 있는가?” 질의해 최종 제외/포함 결정.
- 7일 데이터는 “제목 + 요약(또는 키워드)”를 함께 저장해 비교 정확도를 높임.

---

## 9. 웹 UI

- **스택**: FastAPI(백엔드) + React/Vite(프론트). 기본 localhost.
- **기능**: 발송 내역 목록, 요일별 보기, 호별 상세(저장된 마크다운 렌더), 호별 “피드백 남기기” 폼.
- **접근 제어**: 없음(개인용). 클라우드 배포 시 접근 제어는 별도 검토.
- **수집 소스 관리**: UI는 필수 아님. 파일(`config/sources.yaml`) 수작업으로 추가/제거 가능.

---

## 10. 피드백 루프

- **흐름**: 웹에서 “이 호에 대한 피드백” 제출 → `data/feedback/`에 저장 → 다음 파이프라인 실행 시 수집/분석/요약 단계의 프롬프트에 반영.
- **반영**: 가능한 한 스킬 MD 반영. 피드백을 주기적으로 검토해 `skills/collect.md`, `skills/analyze.md`, `skills/summarize.md` 등에 “피드백 요약·규칙”을 반영. 당장은 “저장된 피드백을 읽어 해당 run의 시스템 프롬프트에만 주입”하고, 수동으로 스킬 MD를 업데이트해 개선 루프를 돌릴 수 있도록 설계.

---

## 11. 디렉터리·파일 네이밍

- `agents/` — 에이전트별 진입점 또는 메타. 예: `agents/collector.md`, `agents/analyzer.md` 등.
- `skills/` — `collect.md`, `analyze.md`, `summarize.md`, `dedup.md`, `letter_generate.md`, `publish.md`. frontmatter + 지시문.
- `tools/` — `fetch_rss.py`, `fetch_github.py`, `fetch_x.py`, `send_email.py` 등. 네이밍은 `동작_소스` 또는 `동작_역할`.
- `config/` — `sources.yaml`(수집 소스 목록), `env.example`(API 키·경로 등).
- `data/` — `letters/`, `index/`, `feedback/`, `checkpoints/`.
- `pipeline/`(또는 `runner/`) — 파이프라인 오케스트레이션(단계 순서, 병렬 실행, 체크포인트 읽기/쓰기, A2A payload 호출).
- 프론트: `frontend/`(React/Vite), 백엔드: `backend/`(FastAPI) 또는 repo 루트에 `api/` 등 일관된 이름.

---

## 12. LLM·설정

- **모델 지정**: **설정으로 사용할 모델을 한 개 지정**한다. 폴백(자동 전환) 없음.
- **설정 예**: `config/llm.yaml`에서 `provider`(예: `google` | `openai`)와 `model`(예: `gemini-3-flash-preview`, `gpt-5-mini`)을 지정. 필요 시 `base_url`, `api_key`는 env에서 주입.
- **모델별 모듈**: 프로바이더·모델마다 **엔드포인트, 요청 페이로드, 응답 파싱, 프롬프트 형식**(시스템/유저 메시지 구조, 토큰 제한 등)이 다르므로 **설정에 따라 해당 어댑터 모듈만 사용**하도록 한다.
  - 예: `pipeline/llm/adapters/gemini.py` — Google API 엔드포인트·페이로드·프롬프팅 규칙.
  - 예: `pipeline/llm/adapters/openai.py` — OpenAI API 엔드포인트·페이로드·프롬프팅 규칙.
- **공통 인터페이스**: 모든 어댑터는 동일한 인터페이스(예: `generate(system, user) -> str`)를 구현하고, 러너는 설정에서 선택된 어댑터만 호출한다.
- **권장 기본값**: `gemini-3-flash-preview`(Google). 변경 시 설정만 수정하면 되도록 설계.

---

## 13. 배포·스케줄링 고려

- **로컬**: APScheduler 또는 프로젝트 레벨 스케줄러. 파이프라인 진입점은 CLI(+ 선택적으로 HTTP)로 통일.
- **클라우드**: 설정(경로/DB/URL)만 환경별로 변경. VM에서는 cron/systemd로 동일 CLI 실행. Vercel/Supabase는 프론트·짧은 API·Cron 트리거용; 장시간 파이프라인은 VM 등에서 실행.

---

## 변경 이력

- 2025-02-25: 초안 작성. 병렬 실행·수집 소스 관리(파일 기반 추가/제거) 반영.
- 2025-02-25: LLM 모델 확정 — 1순위 `gemini-3-flash-preview`, 2순위 `gpt-5-mini`.
- 2025-02-25: LLM을 폴백 제거·설정 지정 방식으로 변경. 모델별 어댑터(엔드포인트·페이로드·프롬프팅) 사용 명시.
