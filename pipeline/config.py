"""파이프라인 설정 로더."""
import yaml


def load_sources(path: str) -> list[dict]:
    """YAML 파일에서 sources를 읽고 enabled가 True인 항목만 반환한다."""
    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    sources = data.get("sources") or []
    return [s for s in sources if s.get("enabled") is True]
