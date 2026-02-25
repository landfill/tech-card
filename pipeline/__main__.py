"""CLI: python -m pipeline run [--date YYYY-MM-DD] [--config-dir config] [--data-dir data] [--skills-dir skills]"""
import argparse
from datetime import date
from pathlib import Path

from pipeline.runner import run_pipeline
from pipeline.llm.client import get_llm_client


def main():
    p = argparse.ArgumentParser(description="데일리 인텔리전스 뉴스레터 파이프라인")
    p.add_argument("--date", default=date.today().isoformat(), help="처리할 날짜 YYYY-MM-DD")
    p.add_argument("--config-dir", default="config", help="설정 디렉터리 (sources.yaml, llm.yaml)")
    p.add_argument("--data-dir", default="data", help="데이터 디렉터리")
    p.add_argument("--skills-dir", default="skills", help="스킬 마크다운 디렉터리")
    p.add_argument("--force", action="store_true", help="체크포인트 있어도 재실행")
    args = p.parse_args()
    config_dir = Path(args.config_dir)
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)
    result = run_pipeline(
        args.date,
        args.config_dir,
        args.data_dir,
        args.skills_dir,
        llm_client,
        force=args.force,
    )
    print("Letter saved:", result.get("letter_path"))


if __name__ == "__main__":
    main()
