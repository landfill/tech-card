"""CLI: python -m pipeline [--date YYYY-MM-DD] [--config-dir config] [--data-dir data] [--skills-dir skills]
날짜 미지정 시 현재 날짜 기준 전일(어제)을 사용해 최근 1일치 수집이 진행된다."""
import argparse
import sys
from datetime import date, timedelta
from pathlib import Path

from pipeline.runner import run_pipeline
from pipeline.llm.client import get_llm_client


def _default_date() -> str:
    """날짜 미지정 시 전일(최근 1일치) 반환."""
    return (date.today() - timedelta(days=1)).isoformat()


def main():
    p = argparse.ArgumentParser(description="데일리 인텔리전스 뉴스레터 파이프라인")
    p.add_argument(
        "--date",
        default=None,
        help="처리할 날짜 YYYY-MM-DD. 생략 시 현재 날짜 기준 전일(최근 1일치) 사용",
    )
    p.add_argument("--config-dir", default="config", help="설정 디렉터리 (sources.yaml, llm.yaml)")
    p.add_argument("--data-dir", default="data", help="데이터 디렉터리")
    p.add_argument("--skills-dir", default="skills", help="스킬 마크다운 디렉터리")
    p.add_argument("--force", action="store_true", help="체크포인트 있어도 재실행")
    p.add_argument("--from-step", default=None, help="이 스텝부터 끝까지만 실행 (예: card_generate)")
    args = p.parse_args()
    date_str = args.date or _default_date()
    config_dir = Path(args.config_dir)
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)
    try:
        result = run_pipeline(
            date_str,
            args.config_dir,
            args.data_dir,
            args.skills_dir,
            llm_client,
            force=args.force,
            from_step=args.from_step,
        )
        letter_path = result.get("letter_path")
        items_count = result.get("items_count", 0)
        card_path = result.get("card_path")
        print("Letter saved:", letter_path)
        print("Items in letter:", items_count)
        if card_path:
            print("Card saved:", card_path)
        print("DONE")  # 자동화/스크립트에서 종료 여부 판단용
        sys.exit(0)
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
