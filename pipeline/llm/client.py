"""설정에 따른 LLM 어댑터 인스턴스 생성."""
import logging
from pathlib import Path

from pipeline.llm.adapters.gemini import GeminiAdapter
from pipeline.llm.adapters.openai import OpenAIAdapter
from pipeline.llm.base import LLMAdapter
from pipeline.llm.config import load_llm_config
from pipeline.ops_logging import format_event

logger = logging.getLogger(__name__)


def get_llm_client(config_path: str | Path) -> LLMAdapter:
    """config_path(YAML)를 읽어 provider에 따라 해당 어댑터 인스턴스 반환."""
    cfg = load_llm_config(config_path)
    provider = cfg["provider"]
    model = cfg["model"]
    api_key = cfg.get("api_key") or ""
    logger.info(format_event("llm_client_ready", provider=provider, model=model, api_key_present=bool(api_key)))
    if provider == "google":
        return GeminiAdapter(model=model, api_key=api_key)
    if provider == "openai":
        return OpenAIAdapter(model=model, api_key=api_key)
    raise ValueError(f"Unknown LLM provider: {provider}. Supported: google, openai.")
