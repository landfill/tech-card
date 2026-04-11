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
    p.add_argument("--no-push", action="store_true", help="파이프라인 완료 후 git push 생략")
    p.add_argument("--weekly", action="store_true", help="주간 통합 인사이트 레터 생성 (--date로 주차 지정 가능)")
    p.add_argument(
        "--evolve",
        nargs="?",
        const="all",
        default=None,
        help="프롬프트 진화만 실행 (파이프라인 미실행). 에이전트명 지정 가능 (예: --evolve analyze)",
    )
    args = p.parse_args()
    date_str = args.date or _default_date()
    config_dir = Path(args.config_dir)
    llm_path = config_dir / "llm.yaml"
    if not llm_path.is_file():
        llm_path = config_dir / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)

    # --weekly 모드: 주간 레터 생성
    if args.weekly:
        from pipeline.weekly_runner import run_weekly_pipeline
        anchor = date.fromisoformat(date_str) if args.date else date.today() - timedelta(days=1)
        print(f"Weekly pipeline: {anchor} 포함 주차...")
        try:
            result = run_weekly_pipeline(
                anchor_date=anchor,
                data_dir=args.data_dir,
                skills_dir=args.skills_dir,
                llm_client=llm_client,
                force=args.force,
            )
            print(f"Week: {result['week_id']} ({result['date_range'][0]} ~ {result['date_range'][1]})")
            print(f"Letter: {result['letter_path']}")
            if not args.no_push:
                from pipeline.git_push import auto_push
                push_result = auto_push(args.data_dir, anchor)
                if push_result.get("pushed"):
                    print(f"Git pushed: {push_result['message']}")
            print("DONE")
            sys.exit(0)
        except Exception as e:
            print("ERROR:", e, file=sys.stderr)
            sys.exit(1)

    # --evolve 모드: 프롬프트 진화만 실행하고 종료
    if args.evolve is not None:
        from pipeline.prompt_evolution import evolve_prompt, EVOLUTION_TARGETS
        anchor = date.fromisoformat(date_str) if args.date else date.today()
        targets = (
            list(EVOLUTION_TARGETS.keys())
            if args.evolve == "all"
            else [args.evolve]
        )
        for agent_name in targets:
            print(f"Evolving prompt: {agent_name}...")
            version = evolve_prompt(
                agent_name=agent_name,
                data_dir=args.data_dir,
                skills_dir=args.skills_dir,
                llm_client=llm_client,
                anchor_date=anchor,
                force=True,
            )
            if version:
                print(f"  -> v{version:03d} created")
            else:
                print(f"  -> failed or skipped")
        sys.exit(0)

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

        # git push (--no-push 시 생략)
        if not args.no_push:
            from pipeline.git_push import auto_push
            push_date = date.fromisoformat(date_str) if args.date else date.today()
            push_result = auto_push(args.data_dir, push_date)
            if push_result.get("pushed"):
                print(f"Git pushed: {push_result['message']}")
            elif push_result.get("committed"):
                print(f"Git committed ({push_result['message']}) but push failed: {push_result.get('error', '')}")
            else:
                reason = push_result.get("message") or push_result.get("error", "")
                print(f"Git skip: {reason}")

        print("DONE")
        sys.exit(0)
    except Exception as e:
        print("ERROR:", e, file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
