---
name: collect
description: 수집 단계 메타. 실제 수집은 pipeline/collect.run_collect가 수행.
---
# Collect
이 스킬은 수집 단계의 목적을 정의한다. 실행은 run_collect()가 config/sources.yaml의 enabled 소스를 병렬로 수집하여 체크포인트에 저장한다.
