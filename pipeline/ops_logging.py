"""Shared operator-facing logging helpers."""
from __future__ import annotations

import json


def format_event(event: str, **fields: object) -> str:
    parts = [f"event={event}"]
    for key, value in fields.items():
        if value is None:
            continue
        if isinstance(value, (dict, list, tuple)):
            rendered = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
        else:
            rendered = str(value)
        if " " in rendered:
            rendered = json.dumps(rendered, ensure_ascii=False)
        parts.append(f"{key}={rendered}")
    return " ".join(parts)
