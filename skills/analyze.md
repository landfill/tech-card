---
name: analyze
description: 수집 결과를 도메인별로 분류하고 핵심 이슈 추출
---
# Analyze
수집된 raw 항목(제목, url, summary, published, source_id)을 다음 카테고리로 분류하라.
- 에이전틱 코딩 & 프론티어 모델 (Claude Code, Cursor, Codex 등)
- GitHub & 인프라 트렌드
- 산업별 AX (트래블, 한국 IT 등)
각 항목에 제목, 요약, 출처(url), 카테고리, 영향도(high/medium/low)를 부여하라. JSON 배열로 출력하라.
