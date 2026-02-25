"""Gemini 어댑터. Google API 엔드포인트·페이로드·프롬프팅 규칙."""
import google.generativeai as genai

from pipeline.llm.base import LLMAdapter


class GeminiAdapter(LLMAdapter):
    """Google Gemini API. 시스템/유저 메시지를 Gemini 메시지 형식으로 변환 후 호출."""

    def __init__(self, model: str, api_key: str):
        genai.configure(api_key=api_key)
        self._model_name = model

    def generate(self, system: str, user: str) -> str:
        model = genai.GenerativeModel(
            model_name=self._model_name,
            system_instruction=system,
        )
        resp = model.generate_content(user)
        if not resp.candidates:
            return ""
        return resp.candidates[0].content.parts[0].text
