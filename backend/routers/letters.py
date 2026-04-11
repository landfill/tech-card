"""발송 내역 API."""
import json
from datetime import date, datetime, timezone
from pathlib import Path

import yaml
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse

from backend.paths import get_data_dir, get_config_dir
from pipeline.checkpoint import clear_checkpoints_for_date, load_checkpoint
from pipeline.storage import index_path, letter_path, card_path, card_bg_image_path

router = APIRouter()


def _data_dir() -> Path:
    return get_data_dir()


def _source_id_to_label(sources_config: list[dict]) -> dict[str, str]:
    """소스 id -> 간단 표기명. sources.yaml의 sources 리스트 기준."""
    out = {}
    for s in sources_config or []:
        sid = (s.get("id") or "").strip()
        if not sid:
            continue
        stype = (s.get("type") or "").strip().lower()
        if stype == "reddit_rss":
            sub = (s.get("subreddit") or "").strip() or sid
            out[sid] = f"r/{sub}"
        elif stype == "hnrss":
            out[sid] = "HN"
        elif stype == "github_blog":
            out[sid] = "GitHub Blog"
        elif stype == "rss":
            out[sid] = sid
        elif stype == "twitter_cli":
            query = (s.get("query") or "")[:30]
            out[sid] = f"X: {query}" if query else "X"
        elif stype == "rdt_cli":
            sub = (s.get("subreddit") or "").strip()
            query = (s.get("query") or "")[:20]
            if sub and query:
                out[sid] = f"r/{sub} ({query})"
            elif sub:
                out[sid] = f"r/{sub}"
            elif query:
                out[sid] = f"Reddit: {query}"
            else:
                out[sid] = sid
        elif stype == "crawl":
            out[sid] = sid
        else:
            out[sid] = sid
    return out


@router.get("")
def list_letters():
    """발송된 레터 날짜 목록 (날짜순)."""
    letters_dir = _data_dir() / "letters"
    if not letters_dir.is_dir():
        return []
    dates = []
    for f in letters_dir.glob("*.md"):
        try:
            dates.append(f.stem)
        except Exception:
            pass
    return sorted(dates, reverse=True)


@router.get("/by-weekday")
def list_letters_by_weekday():
    """요일별 그룹."""
    letters_dir = _data_dir() / "letters"
    if not letters_dir.is_dir():
        return {}
    weekdays = "월화수목금토일"
    by_wd = {w: [] for w in weekdays}
    for f in sorted(letters_dir.glob("*.md"), key=lambda x: x.stem, reverse=True):
        try:
            from datetime import datetime
            d = datetime.strptime(f.stem, "%Y-%m-%d")
            wd = weekdays[d.weekday()]
            by_wd[wd].append(f.stem)
        except Exception:
            pass
    return by_wd


@router.get("/{date}/info")
def get_letter_info(date: str):
    """해당 날짜 레터 메타정보 (문서 생성 시각, 워크플로 완료 여부: 카드·배경)."""
    letters_dir = _data_dir() / "letters"
    path = letters_dir / f"{date}.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Letter not found")
    stat = path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        d = None
    data_dir = _data_dir()
    card_file = Path(card_path(str(data_dir), d)).resolve() if d else None
    bg_file = Path(card_bg_image_path(str(data_dir), d)).resolve() if d else None
    has_cards = card_file.is_file() if card_file else False
    has_card_bg = bg_file.is_file() if bg_file else False

    sources_used: list[str] = []
    if d:
        collect_cp = load_checkpoint(str(data_dir), d, "collect")
        if collect_cp and isinstance(collect_cp.get("sources_run"), list):
            source_ids = collect_cp["sources_run"]
            config_path = get_config_dir() / "sources.yaml"
            if config_path.is_file():
                try:
                    with open(config_path, encoding="utf-8") as f:
                        cfg = yaml.safe_load(f)
                    id_to_label = _source_id_to_label(cfg.get("sources") or [])
                    sources_used = [id_to_label.get(sid, sid) for sid in source_ids]
                except Exception:
                    sources_used = list(source_ids)
            else:
                sources_used = list(source_ids)

    return {
        "date": date,
        "created_at": mtime.isoformat(),
        "has_cards": has_cards,
        "has_card_bg": has_card_bg,
        "sources_used": sources_used,
    }


@router.get("/{date}/cards")
def get_cards(date: str):
    """해당 날짜 카드뉴스 JSON. 없으면 404."""
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    data_dir = _data_dir()
    path = Path(card_path(str(data_dir), d))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Cards not found")
    return json.loads(path.read_text(encoding="utf-8"))


@router.get("/{date}/card-bg")
def get_card_bg(date: str):
    """해당 날짜 카드 배경 이미지 (1호당 1장). 없으면 404."""
    try:
        d = datetime.strptime(date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    data_dir = _data_dir()
    path = Path(card_bg_image_path(str(data_dir), d))
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Card background not found")
    return FileResponse(path, media_type="image/png")


@router.get("/{date}", response_class=PlainTextResponse)
def get_letter(date: str):
    """해당 날짜 레터 마크다운 본문."""
    letters_dir = _data_dir() / "letters"
    path = letters_dir / f"{date}.md"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="Letter not found")
    return path.read_text(encoding="utf-8")


@router.delete("/{date}", status_code=204)
def delete_letter(date: str):
    """해당 날짜 파이프라인 생성물 및 해당 호 피드백 삭제: 레터, 인덱스, 체크포인트, 피드백."""
    from datetime import date as date_cls
    try:
        d = date_cls.fromisoformat(date)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date")
    data_dir = _data_dir()
    # 실행 중이면 삭제 거부
    from pipeline.run_status import read_run_status
    run = read_run_status(str(data_dir), d)
    if run and run.get("running"):
        raise HTTPException(status_code=409, detail="파이프라인 실행 중에는 삭제할 수 없습니다.")
    letter_file = Path(letter_path(str(data_dir), d))
    if letter_file.is_file():
        letter_file.unlink()
    index_file = Path(index_path(str(data_dir), d))
    if index_file.is_file():
        index_file.unlink()
    card_file = Path(card_path(str(data_dir), d))
    if card_file.is_file():
        card_file.unlink()
    card_bg = Path(card_bg_image_path(str(data_dir), d))
    if card_bg.is_file():
        card_bg.unlink()
    clear_checkpoints_for_date(str(data_dir), d)
    # 해당 호 피드백 파일 삭제
    feedback_file = data_dir / "feedback" / f"{date}.json"
    if feedback_file.is_file():
        feedback_file.unlink()
    return None
