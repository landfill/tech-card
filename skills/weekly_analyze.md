---
name: weekly_analyze
description: 7일 수집 데이터에서 주간 트렌드맵, 카테고리 통계, Top5를 추출 (에이전틱 코딩 & 인프라 집중)
---
# Weekly Analyze

입력된 7일간의 뉴스 항목(items)을 분석하여 주간 트렌드 메타데이터를 JSON으로 출력하라.
**입력 항목만 분석할 것. 입력에 없는 정보를 추론하거나 추가하지 말 것.**

## 분석 대상
- **에이전틱 코딩 & 프론티어 모델** (Claude Code, Cursor, Codex, Composer, Copilot 등)
- **GitHub & 인프라 트렌드** (CI/CD, 오픈소스, 인프라)

## 분석 항목

### 1. trend_map (주간 트렌드맵)
같은 주제/제품이 여러 날에 걸쳐 등장하는 패턴을 탐지하라.
- **topic**: 주제명 (예: "Claude Code", "Codex CLI", "GitHub Copilot")
- **days**: 등장한 날짜들 (MM-DD 형식)
- **impact**: 해당 주제의 최고 영향도 ("high"/"medium"/"low")
- **direction**: 트렌드 방향
  - `"sustained"`: 3일 이상 반복 등장
  - `"rising"`: 이번 주 처음 등장 + impact high
  - `"steady"`: 2일 등장 또는 지속적으로 언급
  - `"fading"`: 전주(prev_week_meta)에 있었으나 이번 주 1일 이하

### 2. category_stats (카테고리별 통계)
각 카테고리의 항목 수와 high impact 항목 수.

### 3. top5 (주간 Top 5 하이라이트)
영향도(impact) + 등장 빈도를 종합하여 이번 주 가장 중요한 5개 뉴스.
- **title**: 뉴스 제목
- **url**: 원본 URL
- **mentions**: 등장 횟수 (유사 제목 포함)
- **impact**: 영향도

### 4. daily_counts (일별 항목 수)
각 날짜별 필터링된 항목 수.

## 출력 형식 (JSON만 출력)

```json
{
  "week": "YYYY-Www",
  "date_range": ["YYYY-MM-DD", "YYYY-MM-DD"],
  "total_items": 0,
  "filtered_items": 0,
  "trend_map": [
    {"topic": "...", "days": ["MM-DD"], "impact": "high", "direction": "sustained"}
  ],
  "category_stats": {
    "에이전틱 코딩 & 프론티어 모델": {"count": 0, "high_count": 0},
    "GitHub & 인프라 트렌드": {"count": 0, "high_count": 0}
  },
  "top5": [
    {"title": "...", "url": "...", "mentions": 0, "impact": "high"}
  ],
  "daily_counts": {"YYYY-MM-DD": 0}
}
```

코드 블록 없이 **JSON만** 출력하라.
