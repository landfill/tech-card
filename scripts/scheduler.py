"""APScheduler로 매일 파이프라인 실행. 전일(최근 1일치) 기준으로 수집·레터 생성."""
import logging
from datetime import date, timedelta
from pathlib import Path

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from pipeline.runner import run_pipeline
from pipeline.llm.client import get_llm_client

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"
DATA_DIR = Path(__file__).resolve().parent.parent / "data"
SKILLS_DIR = Path(__file__).resolve().parent.parent / "skills"


def _get_llm_client():
    llm_path = CONFIG_DIR / "llm.yaml"
    if not llm_path.is_file():
        llm_path = CONFIG_DIR / "llm.yaml.example"
    return get_llm_client(llm_path)


def daily_job():
    """전일(최근 1일치) 기준 일간 파이프라인."""
    target_date = (date.today() - timedelta(days=1)).isoformat()
    logger.info("Running daily pipeline for %s", target_date)
    llm_client = _get_llm_client()
    run_pipeline(target_date, str(CONFIG_DIR), str(DATA_DIR), str(SKILLS_DIR), llm_client)
    # auto push
    try:
        from pipeline.git_push import auto_push
        auto_push(str(DATA_DIR), date.today() - timedelta(days=1))
    except Exception:
        pass
    logger.info("Daily pipeline done for %s", target_date)


def weekly_job():
    """매주 월요일: 직전 주(월~일) 기준 주간 레터 생성."""
    from pipeline.weekly_runner import run_weekly_pipeline
    yesterday = date.today() - timedelta(days=1)  # 일요일
    logger.info("Running weekly pipeline for week containing %s", yesterday)
    llm_client = _get_llm_client()
    result = run_weekly_pipeline(
        anchor_date=yesterday,
        data_dir=str(DATA_DIR),
        skills_dir=str(SKILLS_DIR),
        llm_client=llm_client,
    )
    try:
        from pipeline.git_push import auto_push
        auto_push(str(DATA_DIR), date.today())
    except Exception:
        pass
    logger.info("Weekly pipeline done: %s", result.get("week_id"))


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(daily_job, CronTrigger(hour=6, minute=0))
    scheduler.add_job(weekly_job, CronTrigger(day_of_week="mon", hour=7, minute=0))
    logger.info("Scheduler started. Daily at 06:00, Weekly on Mon 07:00.")
    scheduler.start()
