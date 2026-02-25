"""OpenAI 어댑터. OpenAI API 엔드포인트·페이로드·프롬프팅 규칙."""
from openai import OpenAI

from pipeline.llm.base import LLMAdapter


class OpenAIAdapter(LLMAdapter):
    """OpenAI Chat Completions API. 시스템/유저 메시지를 messages 배열로 전달."""

    def __init__(self, model: str, api_key: str):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def generate(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        if not resp.choices:
            return ""
        return resp.choices[0].message.content or ""
