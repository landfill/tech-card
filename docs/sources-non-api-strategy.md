# 비(非) API 수집 전략: RSS 브릿지 + AI 스크래핑

API 비용·제한 없이 뉴스레터 품질을 높이기 위한 수집 소스 전략 요약.  
실제 소스 목록은 `config/sources.yaml`에서 관리한다.

---

## 1. 소셜 미디어(X, Threads) 및 커뮤니티: RSS 브릿지

- **RSS-bridge**: X(트위터), Threads, Instagram 등 비RSS 사이트를 RSS 피드로 변환하는 오픈소스.  
  - 특정 인플루언서 계정 또는 키워드 검색을 RSS로 구독 가능.  
  - 자체 호스트 또는 공개 인스턴스 `bridge_url` 지정.
- **hnrss.org**: Hacker News 검색·점수 필터를 RSS로 제공.  
  - 예: "Agentic", "Cursor" 등 키워드, 특정 점수 이상만 수집.
- **Reddit RSS**: 서브레딧 URL에 `.rss` 추가 (예: `https://www.reddit.com/r/ClaudeAI.rss`).  
  - API 없이 최신 포스트 수집.

---

## 2. 에이전틱 코딩·GitHub 트렌드

- **GitHub Trending RSS (비공식)**: 데일리/위클리 트렌딩을 언어별 RSS로 변환.  
  - 에이전틱·AI 관련 신규 프로젝트 감지용.
- **GitHub Blog**: 공식 AI·ML 업데이트.  
  - `https://github.blog/feed/` 또는 섹션별 피드.

---

## 3. 동적 웹·릴리스 노트: Firecrawl / 헤드리스

- **Firecrawl**: URL 입력 시 AI가 마크다운·JSON으로 변환.  
  - Cursor changelog, Anthropic news 등 JS 중첩 페이지 감시(Watch)에 적합.
- **ScrapingBee / Puppeteer**: 헤드리스 브라우저로 SPA 렌더 후 추출.  
  - 기술 블로그가 SPA인 경우 단순 크롤러 대신 사용.

---

## 4. 국내 IT·트래블 도메인

- **전자신문·디지털데일리**: 섹션별 RSS(보안, AI, 전자 등).  
- **Phocuswire AI Stories**: 트래블 도메인 AI 에이전트 사례.  
- **Skift Digital**: 여행 산업 디지털·에이전트.  
  - RSS가 없으면 RSS.app 등으로 피드 생성 후 `type: rss`로 등록.

---

## 5. 워크플로: 중복 제거·그룹링

- **n8n / Make.com** 등으로 수집 후 토픽 그룹링·유사도 임계값(예: 80%) 적용 가능.  
- 파이프라인 내 **의미적 중복 제거**는 설계 문서의 7일 인덱스 + 임베딩·LLM 판정으로 수행.

---

## type ↔ 툴 매핑 (구현 시 참고)

| type | 수집 툴 | 비고 |
|------|--------|------|
| rss | fetch_rss | feedparser 등 |
| rss_bridge | fetch_rss_bridge | bridge_url + bridge + account/search_query |
| hnrss | fetch_hnrss | hnrss.org 쿼리·points_min |
| reddit_rss | fetch_rss | URL: https://www.reddit.com/r/{subreddit}.rss |
| github_trending_rss | fetch_github_trending_rss | 비공식 RSS URL 생성 또는 스크래핑 |
| github_blog | fetch_rss | url 그대로 RSS |
| firecrawl | fetch_firecrawl | Firecrawl API (크롤러 모드) |
| headless | fetch_headless | Puppeteer/ScrapingBee |
