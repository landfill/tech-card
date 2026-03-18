"""LLM 설정 로드. config/llm.yaml + env."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

# 프로젝트 루트의 .env 로드 (CLI/서버 실행 시 cwd 기준)
load_dotenv()


def load_llm_config(config_path: str | Path) -> dict:
    """config_path(YAML)에서 provider, model 로드. api_key는 env에서 주입."""
    path = Path(config_path)
    if not path.is_file():
        raise FileNotFoundError(f"LLM config not found: {config_path}")
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    provider = (data.get("provider") or "").strip().lower()
    model = (data.get("model") or "").strip()
    if not provider or not model:
        raise ValueError("LLM config must have 'provider' and 'model'")
    api_key = None
    if provider == "google":
        api_key = os.environ.get("GOOGLE_API_KEY")
    elif provider == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
    return {
        "provider": provider,
        "model": model,
        "api_key": api_key,
    }
