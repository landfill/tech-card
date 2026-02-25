"""발행: 레터 본문 읽어 수신자에게 메일 발송."""
from datetime import date, datetime
from pathlib import Path

from pipeline.storage import letter_path
from tools.send_email import load_subscribers, send_email


def publish(date_str: str, data_dir: str | Path, subject_prefix: str = "Daily Intelligence") -> None:
    """data/letters/{date}.md를 읽어 구독자에게 발송. subject = {prefix} {date}."""
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
    send_email(to_list, subject, body)
