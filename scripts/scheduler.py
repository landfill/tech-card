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


def job():
    # 전일(최근 1일치) 기준
    target_date = (date.today() - timedelta(days=1)).isoformat()
    logger.info("Running pipeline for %s (전일 1일치)", target_date)
    llm_path = CONFIG_DIR / "llm.yaml"
    if not llm_path.is_file():
        llm_path = CONFIG_DIR / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)
    run_pipeline(target_date, str(CONFIG_DIR), str(DATA_DIR), str(SKILLS_DIR), llm_client)
    logger.info("Pipeline done for %s", target_date)


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(job, CronTrigger(hour=6, minute=0))
    logger.info("Scheduler started. Daily at 06:00.")
    scheduler.start()
