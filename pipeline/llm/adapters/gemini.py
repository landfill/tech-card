"""Gemini 어댑터. Google API 엔드포인트·페이로드·프롬프팅 규칙."""
from google import genai
from google.genai.types import GenerateContentConfig

from pipeline.llm.base import LLMAdapter


class GeminiAdapter(LLMAdapter):
    """Google Gemini API. 시스템/유저 메시지를 Gemini 메시지 형식으로 변환 후 호출."""

    def __init__(self, model: str, api_key: str):
        self._client = genai.Client(api_key=api_key)
        self._model_name = model

    def generate(self, system: str, user: str) -> str:
        config = GenerateContentConfig(system_instruction=system)
        resp = self._client.models.generate_content(
            model=self._model_name,
            contents=user,
            config=config,
        )
        return getattr(resp, "text", "") or ""
