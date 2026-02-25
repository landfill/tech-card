"""APScheduler로 매일 파이프라인 실행."""
import logging
from datetime import date
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
    today = date.today().isoformat()
    logger.info("Running pipeline for %s", today)
    llm_path = CONFIG_DIR / "llm.yaml"
    if not llm_path.is_file():
        llm_path = CONFIG_DIR / "llm.yaml.example"
    llm_client = get_llm_client(llm_path)
    run_pipeline(today, str(CONFIG_DIR), str(DATA_DIR), str(SKILLS_DIR), llm_client)
    logger.info("Pipeline done for %s", today)


if __name__ == "__main__":
    scheduler = BlockingScheduler()
    scheduler.add_job(job, CronTrigger(hour=6, minute=0))
    logger.info("Scheduler started. Daily at 06:00.")
    scheduler.start()
