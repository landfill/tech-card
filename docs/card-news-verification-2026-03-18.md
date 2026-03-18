# 카드뉴스 확장 검증 보고서

- **검증 일시**: 2026-03-18
- **검증자**: 파이프라인/백엔드/API 자동 검증
- **사용 데이터**: 날짜 `2026-03-16`, 기존 레터 `data/letters/2026-03-16.md` 기준

---

## 1. card_generate 단독 실행

| 항목 | 결과 | 비고 |
|------|------|------|
| `--from-step card_generate` 실행 | 통과 | `uv run python -m pipeline --date 2026-03-16 --from-step card_generate --force` |
| `data/cards/2026-03-16.json` 생성 | 통과 | 파일 존재, 스키마 정상 |
| cards 배열 구조 | 통과 | type, title, body[] 필드, 6장(cover, highlight, news×2, insight, closing) |
| bgImage 필드 | 통과 | `null` (config/images.yaml 미설정 시 스킵) |

---

## 2. card_backgrounds

| 항목 | 결과 | 비고 |
|------|------|------|
| 체크포인트 저장 | 통과 | `data/checkpoints/2026-03-16/card_backgrounds.json` 존재 |
| 배경 이미지 생성 | 스킵 | `config/images.yaml` 없거나 api_key 비어 있어 1호당 1장 생성 생략 |
| JSON 보강 | 통과 | `bgImage: null` 유지 (그라디언트 폴백용) |

---

## 3. API

| 항목 | 결과 | 비고 |
|------|------|------|
| `GET /api/letters/2026-03-16/cards` | 통과 | 200, JSON 본문 정상 (date, cards, bgImage) |
| `GET /api/letters/2026-03-16/card-bg` | 통과 | 404 (배경 이미지 없음) |
| `GET /api/letters/2026-03-17/cards` | 통과 | 404 (카드 미생성 날짜) |
| 잘못된 날짜 형식 | 통과 | 400 |

---

## 4. 프론트엔드

| 항목 | 결과 | 비고 |
|------|------|------|
| 빌드 | 통과 | `npm run build` 성공 |
| 카드 뷰 진입·복귀 | 미실행 | 백엔드 기동 후 브라우저에서 "카드로 보기" → 카드 뷰, "본문 보기" 복귀 수동 확인 권장 |
| 배경 이미지/그라디언트 | 설계 반영 | bgImage 없을 때 그라디언트 폴백 적용됨 |

---

## 5. 요약

- **card_generate**: 기존 레터 파일만으로 `from_step=card_generate` 실행 시 카드 JSON 정상 생성됨.
- **card_backgrounds**: API 키 미설정 시 스킵, 체크포인트·JSON 보강 정상.
- **백엔드 API**: `/cards`, `/card-bg` 응답 코드·본문 검증 완료.
- **한계·권장**: (1) 배경 이미지 검증은 `config/images.yaml`에 provider·api_key 설정 후 재실행 필요. (2) 프론트 "카드로 보기"·스와이프·키보드 네비는 브라우저에서 1회 수동 확인 권장.
