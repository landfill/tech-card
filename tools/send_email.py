"""메일 발송. M365 SMTP (STARTTLS, port 587) 지원.
.env 설정: SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM
미설정 시 로그만 출력(스텁 모드)."""
import json
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import markdown

logger = logging.getLogger(__name__)


def _smtp_config() -> dict | None:
    """환경변수에서 SMTP 설정 로드. 필수값 없으면 None."""
    user = os.environ.get("SMTP_USER", "").strip()
    password = os.environ.get("SMTP_PASSWORD", "").strip()
    if not user or not password:
        return None
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.office365.com").strip(),
        "port": int(os.environ.get("SMTP_PORT", "587")),
        "user": user,
        "password": password,
        "from_addr": os.environ.get("SMTP_FROM", user).strip(),
    }


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


def _md_to_html(body_md: str) -> str:
    """마크다운을 HTML로 변환. 뉴스레터용 인라인 스타일 래핑."""
    html_body = markdown.markdown(body_md, extensions=["tables", "fenced_code"])
    return f"""\
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; \
line-height: 1.8; color: #1a1a1a; max-width: 680px; margin: 0 auto; padding: 24px;">
{html_body}
<hr style="border: none; border-top: 1px solid #e0e0e0; margin: 32px 0 16px;">
<p style="font-size: 12px; color: #888;">이 메일은 Daily Intelligence Newsletter 자동 발송입니다.</p>
</body>
</html>"""


def send_email(to_list: list[str], subject: str, body_md: str) -> dict:
    """메일 발송. SMTP 설정 있으면 실제 발송, 없으면 스텁.
    반환: {sent: bool, recipients: int, error: str|None}"""
    if not to_list:
        return {"sent": False, "recipients": 0, "error": "수신자 없음"}

    cfg = _smtp_config()
    if cfg is None:
        for to in to_list:
            logger.info("(stub) send_email to=%s subject=%s", to, subject)
        return {"sent": False, "recipients": len(to_list), "error": "SMTP 미설정 (스텁 모드)"}

    html = _md_to_html(body_md)

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"], timeout=30) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(cfg["user"], cfg["password"])

            sent_count = 0
            for to in to_list:
                msg = MIMEMultipart("alternative")
                msg["From"] = cfg["from_addr"]
                msg["To"] = to
                msg["Subject"] = subject
                msg.attach(MIMEText(body_md, "plain", "utf-8"))
                msg.attach(MIMEText(html, "html", "utf-8"))
                server.sendmail(cfg["from_addr"], to, msg.as_string())
                sent_count += 1
                logger.info("Email sent: to=%s subject=%s", to, subject)

        return {"sent": True, "recipients": sent_count, "error": None}
    except Exception as e:
        logger.error("Email send failed: %s", e)
        return {"sent": False, "recipients": 0, "error": str(e)}
