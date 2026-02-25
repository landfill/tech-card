"""피드백 저장소. 호별 data/feedback/YYYY-MM-DD.json."""
import json
import os
from datetime import date, datetime, timezone


def save_feedback(
    data_dir: str,
    issue_date: date,
    feedback_type: str,
    content: str,
) -> None:
    """한 건의 피드백을 해당 호(issue_date) 파일에 append한다."""
    dirpath = os.path.join(data_dir, "feedback")
    os.makedirs(dirpath, exist_ok=True)
    path = os.path.join(dirpath, f"{issue_date.isoformat()}.json")
    entry = {
        "issue_date": issue_date.isoformat(),
        "type": feedback_type,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    existing = []
    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            existing = json.load(f)
    existing.append(entry)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(existing, f, ensure_ascii=False, indent=2)


def load_feedback_since(data_dir: str, cutoff_date: date) -> list[dict]:
    """cutoff_date 이후(이상) issue_date인 피드백을 모두 모아 반환. 최신순."""
    dirpath = os.path.join(data_dir, "feedback")
    if not os.path.isdir(dirpath):
        return []
    results = []
    for name in os.listdir(dirpath):
        if not name.endswith(".json"):
            continue
        try:
            d = date.fromisoformat(name[:-5])
        except ValueError:
            continue
        if d < cutoff_date:
            continue
        path = os.path.join(dirpath, name)
        with open(path, encoding="utf-8") as f:
            items = json.load(f)
        for item in items:
            item["_issue_date"] = d.isoformat()
            results.append(item)
    results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    return results
