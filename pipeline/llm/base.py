"""LLM 어댑터 공통 인터페이스."""
from abc import ABC, abstractmethod


class LLMAdapter(ABC):
    """설정으로 선택된 단일 모델과 통신하는 어댑터. 엔드포인트·페이로드·프롬프팅은 구현체에만 둔다."""

    @abstractmethod
    def generate(self, system: str, user: str) -> str:
        """시스템 프롬프트와 유저 메시지로 한 번 생성 후 응답 텍스트 반환."""
        ...
