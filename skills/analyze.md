---
name: analyze
description: 수집 결과를 도메인별로 분류하고 핵심 이슈 추출
---
# Analyze
수집된 raw 항목(제목, url, summary, published, source_id)을 다음 카테고리로 분류하라.
**입력으로 전달된 항목만 분류·출력할 것. 목록에 없는 뉴스·발표·URL은 절대 추가하지 말 것.**

- 에이전틱 코딩 & 프론티어 모델 (Claude Code, Cursor, Codex, Composer 등)
- GitHub & 인프라 트렌드 (CI/CD, 오픈소스, 인프라)
- 산업별 AX (트래블, 금융, 제조 등 산업별 AI·경험)
- 대한민국 IT (한국 기업·정책·시장·국내 언론·국산 기술 관련)
각 항목에 제목, 요약, 출처(url), 카테고리, 영향도(high/medium/low)를 부여하라. JSON 배열로 출력하라.
