# 카드뉴스 확장 구현 후 검증 체크리스트

구현 완료 후 아래 항목을 셀프 검증하고, 결과를 `docs/card-news-verification-YYYYMMDD.md`에 레포팅한다.

## 검증 항목

- [ ] **card_generate 단독 실행**  
  기존 레터가 있는 날짜(예: `data/letters/2026-03-16.md`)에 대해  
  `from_step=card_generate`로 파이프라인 실행 → `data/cards/YYYY-MM-DD.json` 생성·스키마·내용 확인.

- [ ] **card_backgrounds**  
  `config/images.yaml`에 provider·api_key 설정 시 배경 이미지 1장 생성(`data/cards/YYYYMMDD.png`). provider: google(구글 공식 Imagen) | nanobanana.  
  미설정 시 스킵되고 JSON에 `bgImage` 없음 또는 null.

- [ ] **API**  
  `GET /api/letters/{date}/cards` → 카드 JSON 반환.  
  `GET /api/letters/{date}/card-bg` → 이미지 반환(있을 때).

- [ ] **프론트**  
  레터 상세에서 "카드로 보기" 클릭 → 카드 뷰·진행 바·이전/다음·키보드 좌우·스와이프 동작.  
  배경 이미지 있으면 표시, 없으면 그라디언트 폴백.  
  "본문 보기"로 복귀.

- [ ] **(선택) 전체 파이프라인**  
  한 날짜에 대해 collect부터 card_backgrounds까지 실행 → 정상 종료 여부.

## 레포팅 예시

`docs/card-news-verification-YYYYMMDD.md`:

- 검증 일시
- 사용한 날짜/데이터
- 항목별 통과 여부
- 이슈·한계점 요약
