# PlantUML 다이어그램

프로젝트 코드베이스 분석 결과를 바탕으로 한 PlantUML 다이어그램 모음입니다.

## 파일 목록

| 파일 | 설명 |
|------|------|
| `components.puml` | **시스템 컴포넌트**: Frontend, Backend, Pipeline, LLM, Tools, Config/Data 간 의존 관계 |
| `pipeline-activity.puml` | **파이프라인 활동도**: collect → analyze → summarize → dedup → letter_generate 단계 흐름 |
| `pipeline-sequence.puml` | **파이프라인 시퀀스**: CLI/API 호출 시 runner·collect·agents·dedup·letter_generate·checkpoint 간 호출 순서 |
| `llm-class.puml` | **LLM 클래스 다이어그램**: LLMAdapter 추상 클래스와 GeminiAdapter, OpenAIAdapter 구현체, client/config 모듈 |
| `deployment.puml` | **배포/실행 환경**: 브라우저·Vite·uvicorn·CLI·scheduler와 config/data/skills·외부 API 관계 |

## 보는 방법

### 1. VS Code / Cursor

- [PlantUML 확장](https://marketplace.visualstudio.com/items?itemName=jebbs.plantuml) 설치 후 `.puml` 파일에서 `Alt+D` 또는 우클릭 → "Preview Current Diagram".

### 2. CLI (Java 필요)

```bash
# PlantUML jar 다운로드 후
java -jar plantuml.jar docs/plantuml/*.puml
# PNG는 같은 디렉터리에 생성됨
```

### 3. 온라인

- [PlantUML Online Server](https://www.plantuml.com/plantuml/uml/) 에서 각 `.puml` 내용 붙여넣기.

### 4. 다이어그램 서버 (로컬)

```bash
# Docker
docker run -d -p 8080:8080 plantuml/plantuml-server:jetty
# 브라우저에서 http://localhost:8080 → .puml 업로드 또는 텍스트 입력
```

## 프로젝트 구조 요약

- **Frontend**: Vite + React, 발송 내역·파이프라인 탭, Backend API 호출.
- **Backend**: FastAPI, `/api/letters`, `/api/feedback`, `/api/pipeline` (상태·실행·단계 실행).
- **Pipeline**: `runner`가 collect → analyze → summarize → dedup → letter_generate 순서로 실행, 단계별 체크포인트 저장.
- **LLM**: `config/llm.yaml` + env의 provider/model에 따라 `GeminiAdapter` 또는 `OpenAIAdapter` 사용.
- **Tools**: RSS/hnrss/reddit_rss/crawl 수집기, `send_email` 등.
- **Data**: `data/letters/`, `data/checkpoints/`, `data/index/`, `data/feedback/`, `skills/*.md`.
