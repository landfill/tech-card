"""카드 배경 이미지 설정 로드. config/images.yaml + .env (llm 설정 방식과 동일)."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()


def load_image_config(config_dir: str | Path) -> dict | None:
    """
    config_dir/images.yaml에서 선택 옵션(모델 등) 로드.
    api_key는 .env의 GOOGLE_API_KEY 사용 (배경 이미지 생성 고정).
    키가 없으면 None 반환.
    """
    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key or not api_key.strip():
        return None
    api_key = api_key.strip()

    result = {"api_key": api_key}
    path = Path(config_dir) / "images.yaml"
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
        if data.get("model"):
            result["model"] = (data["model"] or "").strip()
    return result
