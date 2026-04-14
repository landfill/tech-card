"""발행: 레터 본문 읽어 수신자에게 메일 발송. 주간 레터도 지원."""
import logging
from datetime import date, datetime
from pathlib import Path

from pipeline.storage import letter_path, weekly_letter_path
from tools.send_email import load_subscribers, send_email

logger = logging.getLogger(__name__)


def _publish_outcome(result: dict) -> str:
    if result.get("sent"):
        return "succeeded"
    error = (result.get("error") or "").strip()
    if error == "수신자 없음":
        return "no_recipients"
    if "스텁" in error:
        return "stub"
    return "failed"


def publish(date_str: str, data_dir: str | Path, subject_prefix: str = "Daily Intelligence") -> dict:
    """일간 레터 발송. 반환: send_email 결과 dict."""
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        d = date.today()
    path = letter_path(str(data_dir), d)
    if not Path(path).is_file():
        raise FileNotFoundError(f"Letter not found: {path}")
    body = Path(path).read_text(encoding="utf-8")
    to_list = load_subscribers(data_dir)
    subject = f"{subject_prefix} {date_str}"
    result = send_email(to_list, subject, body)
    logger.info(
        "event=integration_email date=%s outcome=%s recipients=%s error=%s",
        date_str,
        _publish_outcome(result),
        result.get("recipients", 0),
        result.get("error"),
    )
    return result


def publish_weekly(week_id: str, data_dir: str | Path) -> dict:
    """주간 레터 발송. 반환: send_email 결과 dict."""
    path = weekly_letter_path(str(data_dir), week_id)
    if not Path(path).is_file():
        raise FileNotFoundError(f"Weekly letter not found: {path}")
    body = Path(path).read_text(encoding="utf-8")
    to_list = load_subscribers(data_dir)
    subject = f"Weekly Intelligence {week_id}"
    result = send_email(to_list, subject, body)
    logger.info(
        "event=integration_email week=%s outcome=%s recipients=%s error=%s",
        week_id,
        _publish_outcome(result),
        result.get("recipients", 0),
        result.get("error"),
    )
    return result
