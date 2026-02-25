"""LLM 설정·어댑터 (설정 기반 단일 모델)."""
from pipeline.llm.client import get_llm_client
from pipeline.llm.config import load_llm_config

__all__ = ["get_llm_client", "load_llm_config"]
