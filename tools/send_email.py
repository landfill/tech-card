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


def _preprocess_letter_md(body_md: str) -> str:
    """레터 마크다운을 표준 마크다운 헤딩으로 전처리.
    레터 구조: 첫 줄=제목, 빈 줄 뒤 본문, '1. 섹션명: ...' = h2, '**[항목]:**' = h3 스타일."""
    import re
    lines = body_md.split("\n")
    result = []
    for i, line in enumerate(lines):
        stripped = line.strip()
        # 첫 줄(비어있지 않은 첫 줄)을 h1으로
        if i == 0 and stripped and not stripped.startswith("#"):
            result.append(f"# {stripped}")
            continue
        # "1. 섹션명: ..." 패턴 → h2 (단, "1. **항목" 형태의 리스트 아이템은 제외)
        m = re.match(r"^(\d+)\.\s+(.+)", stripped)
        if m and not re.match(r"^\d+\.\s+\*\*", stripped) and ":" in m.group(2):
            result.append(f"## {m.group(2)}")
            continue
        # "> 인용" 은 그대로 유지
        # "지속 이슈:", "신규 이슈:" 같은 소제목 → h3
        if stripped in ("지속 이슈:", "신규 이슈:") or re.match(r"^(지속 이슈|신규 이슈|다음 주 주목 포인트)", stripped):
            result.append(f"### {stripped}")
            continue
        # "Top 5 하이라이트", "주간 트렌드맵" 같은 제목 → h2
        if stripped and not stripped.startswith(("#", ">", "|", "-", "*")) and not stripped.startswith("**") and len(stripped) < 40 and i > 0 and (not lines[i-1].strip()):
            # 짧은 독립 줄 = 소제목 후보
            if any(kw in stripped for kw in ["트렌드맵", "하이라이트", "카테고리", "주목 포인트", "주간 정리", "인프라 트렌드", "프론티어 모델", "에이전틱 코딩"]):
                result.append(f"## {stripped}")
                continue
        result.append(line)
    return "\n".join(result)


def _md_to_html(body_md: str) -> str:
    """마크다운을 뉴스레터 HTML 메일 템플릿으로 변환. 인라인 스타일 적용."""
    import re
    preprocessed = _preprocess_letter_md(body_md)
    html_body = markdown.markdown(preprocessed, extensions=["tables", "fenced_code"])

    # ── 인라인 스타일 치환 ──
    tag_styles = {
        "<h1>": "font-size:22px;font-weight:700;color:#1a1a1a;margin:28px 0 12px;padding-bottom:10px;border-bottom:3px solid #5E2BB8;line-height:1.35;",
        "<h2>": "font-size:17px;font-weight:700;color:#1a1a1a;margin:28px 0 14px;padding:10px 16px;background:#f7f3ff;border-radius:6px;line-height:1.35;border-left:4px solid #5E2BB8;",
        "<h3>": "font-size:15px;font-weight:600;color:#5E2BB8;margin:20px 0 8px;padding-left:12px;border-left:3px solid #5E2BB8;line-height:1.35;",
        "<p>": "margin:0 0 16px;line-height:1.85;font-size:15px;color:#2a2a2a;",
        "<blockquote>": "margin:16px 0;padding:14px 18px;border-left:4px solid #5E2BB8;background:#f7f3ff;border-radius:0 8px 8px 0;font-style:italic;color:#4a3a6a;font-size:15px;line-height:1.7;",
        "<table>": "width:100%;border-collapse:collapse;margin:18px 0;font-size:13px;border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;",
        "<thead>": "background:#f7f3ff;",
        "<th>": "padding:10px 12px;border:1px solid #e0e0e0;font-weight:600;text-align:center;color:#5E2BB8;font-size:12px;",
        "<td>": "padding:9px 12px;border:1px solid #e8e8e8;text-align:center;font-size:13px;",
        "<ul>": "padding-left:20px;margin:8px 0 16px;",
        "<ol>": "padding-left:20px;margin:8px 0 16px;",
        "<li>": "margin-bottom:8px;line-height:1.75;font-size:15px;color:#2a2a2a;",
        "<code>": "background:#f0ecf7;padding:2px 6px;border-radius:4px;font-size:13px;font-family:'SF Mono',Consolas,monospace;color:#5E2BB8;",
    }
    for tag, style in tag_styles.items():
        html_body = html_body.replace(tag, f'{tag[:-1]} style="{style}">')

    # 링크
    html_body = html_body.replace("<a ", '<a style="color:#5E2BB8;text-decoration:none;border-bottom:1px solid rgba(94,43,184,0.4);font-weight:500;" ')
    # strong
    html_body = html_body.replace("<strong>", '<strong style="font-weight:600;color:#1a1a1a;">')
    # hr
    for hr in ["<hr>", "<hr/>", "<hr />"]:
        html_body = html_body.replace(hr, '<hr style="border:none;height:1px;background:linear-gradient(to right,#5E2BB8,#08D1D9,#5E2BB8);margin:28px 0;opacity:0.4;">')

    # 트렌드맵 ● 도트 → 보라색 강조
    html_body = html_body.replace("●", '<span style="color:#5E2BB8;font-size:18px;line-height:1;">●</span>')
    # ■ 강도바 → 민트색 강조
    html_body = re.sub(r"(■+)", r'<span style="color:#08D1D9;letter-spacing:2px;font-family:monospace;font-size:14px;">\1</span>', html_body)

    # 첫 번째 줄(헤드라인)을 추출해서 헤더 배너로 사용
    first_line = ""
    lines = body_md.strip().split("\n")
    if lines:
        first_line = lines[0].strip().lstrip("#").strip()

    return f"""\
<!DOCTYPE html>
<html lang="ko">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#f2f0f5;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Malgun Gothic','Apple SD Gothic Neo',sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:#f2f0f5;">
<tr><td align="center" style="padding:24px 16px;">
<table role="presentation" width="640" cellpadding="0" cellspacing="0" style="max-width:640px;width:100%;">

  <!-- 헤더 배너 -->
  <tr><td style="background:#5E2BB8;padding:28px 32px;border-radius:12px 12px 0 0;">
    <p style="margin:0 0 6px;font-size:11px;font-weight:600;color:#08D1D9;text-transform:uppercase;letter-spacing:2px;">DAILY INTELLIGENCE</p>
    <p style="margin:0;font-size:18px;font-weight:700;color:#f0f0f0;line-height:1.4;">{first_line}</p>
  </td></tr>

  <!-- 본문 -->
  <tr><td style="background:#ffffff;padding:32px 32px 24px;border-left:1px solid #e8e4f0;border-right:1px solid #e8e4f0;">
    {html_body}
  </td></tr>

  <!-- 푸터 -->
  <tr><td style="background:#faf9fc;padding:20px 32px;border-radius:0 0 12px 12px;border:1px solid #e8e4f0;border-top:none;">
    <table role="presentation" width="100%" cellpadding="0" cellspacing="0">
    <tr>
      <td style="font-size:12px;color:#888;line-height:1.6;">
        Daily Intelligence Newsletter<br>
        <span style="color:#aaa;">Powered by AI Pipeline &middot; Auto-generated</span>
      </td>
      <td align="right" style="font-size:11px;color:#bbb;">
        <span style="display:inline-block;width:8px;height:8px;background:#5E2BB8;border-radius:50%;margin-right:4px;vertical-align:middle;"></span>
        <span style="display:inline-block;width:8px;height:8px;background:#08D1D9;border-radius:50%;vertical-align:middle;"></span>
      </td>
    </tr>
    </table>
  </td></tr>

</table>
</td></tr>
</table>
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
