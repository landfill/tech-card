"""메일 발송. 1차는 로그 스텁. SMTP/SendGrid 연동 시 확장."""
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def load_subscribers(data_dir: str | Path) -> list[str]:
    """data_dir/subscribers.json에서 이메일 목록 로드."""
    path = Path(data_dir) / "subscribers.json"
    if not path.is_file():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, list) else []
    except Exception:
        return []


def send_email(to_list: list[str], subject: str, body_md: str) -> None:
    """메일 발송. 현재는 로그만. SMTP/SendGrid 연동 시 구현."""
    for to in to_list:
        logger.info("(stub) send_email to=%s subject=%s len(body)=%d", to, subject, len(body_md or ""))
