---
name: card_theme
description: 레터 본문에서 카드 배경 이미지용 핵심 키워드(한 줄) 추출 — 주제를 반영한 배경용
---
# Card Theme

입력된 **레터 마크다운(letter_md)**에서, 그날 호의 **핵심 주제·키워드**를 담은 **한 줄**만 출력하라. 이 키워드는 배경 이미지가 "무슨 뉴스 카드인지" 분위기로 드러내는 데 쓰인다.

## 규칙

- **한 줄만** 출력. 앞뒤 따옴표·코드 블록 없이.
- **영어로** 작성 (이미지 생성 API용).
- **카드 뉴스의 핵심 키워드**를 기반으로 할 것: 레터 헤드라인·오프닝·핵심 소식에서 주제(예: AI coding, IDE, agent workflow, Claude, Cursor, developer tools, GPU, cloud 인프라 등)를 추려 쉼표나 and로 이어 한 문장/구로 정리.
- 지나치게 추상적인 표현만 쓰지 말 것. "soft gradient, minimal"처럼 주제와 무관한 단어만 나오면 안 되고, **반드시 그날 호의 테마·키워드**가 포함되어야 함.
- 예시 (올바른 방향): "AI coding, IDE and agent workflow, Claude and Cursor, subtle tech mood" / "developer tools, code and cloud infrastructure, modern tech" / "AI agents, persistent memory, MCP and skills, minimal tech atmosphere"
- 예시 (피할 것): "soft dark blue gradient with subtle abstract light" — 주제 키워드 없이 분위기만 있는 경우. / "developer at desk with laptop" — 인물·구체적 장면은 배경으로 과함.
- 배경용이므로 **키워드 나열 + "subtle, minimal, no text no people"** 같은 제약은 이미지 생성 단계에서 붙이므로, 여기서는 **주제 키워드**에만 집중하라.
