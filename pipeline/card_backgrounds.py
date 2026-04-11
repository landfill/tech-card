"""카드 배경 이미지 1호당 1장 생성. 구글 공식 Gemini 이미지 생성 API만 사용."""
import json
import logging
from pathlib import Path

from google import genai
from google.genai.types import GenerateContentConfig
from google.genai import types

from pipeline.agents import run_agent
from pipeline.image_config import load_image_config
from pipeline.storage import card_bg_image_path

logger = logging.getLogger(__name__)

GEMINI_IMAGE_MODEL = "gemini-3.1-flash-image-preview"


def extract_theme(letter_md: str, skills_dir, llm_client, data_dir=None) -> str:
    """레터에서 이미지용 한 줄 컨셉 추출."""
    out = run_agent("card_theme", {"letter_md": letter_md}, skills_dir, llm_client, data_dir=data_dir)
    return out.strip().strip('"').strip()


# 카드 배경용: 핵심 키워드를 반영하되, 배경으로 쓸 수 있게 절제된 구도로 유도
_BACKGROUND_PROMPT_PREFIX = (
    "Background image for a news card. The image must visually reflect these themes/keywords so the card feels about this topic. "
    "Style: subtle and minimal, no text, no people, no cluttered scenes — suitable for text overlay. "
    "Evoke the subject matter through mood, color, and simple abstract or suggestive shapes only. Themes: "
)


def _generate_gemini_image(prompt: str, api_key: str, out_path: str, model: str | None = None) -> bool:
    """구글 공식 Gemini generate_content + IMAGE로 1장 생성 후 out_path에 저장. 배경용으로 단순·절제된 구도 유도."""
    try:
        client = genai.Client(api_key=api_key)
        full_prompt = _BACKGROUND_PROMPT_PREFIX + (prompt[:500] if prompt else "abstract soft gradient")
        response = client.models.generate_content(
            model=model or GEMINI_IMAGE_MODEL,
            contents=full_prompt,
            config=GenerateContentConfig(
                response_modalities=[types.Modality.TEXT, types.Modality.IMAGE],
                image_config=types.ImageConfig(aspect_ratio="9:16", image_size="1K"),
            ),
        )
        if not response.candidates:
            logger.warning("Gemini image: no candidates in response")
            return False
        for part in response.candidates[0].content.parts:
            if getattr(part, "inline_data", None) and getattr(part.inline_data, "data", None):
                Path(out_path).parent.mkdir(parents=True, exist_ok=True)
                Path(out_path).write_bytes(part.inline_data.data)
                return True
        logger.warning("Gemini image: no inline_data in response parts")
        return False
    except Exception as e:
        logger.warning("Gemini image error: %s", e)
        return False


def generate_card_background(
    letter_md: str,
    data_dir: str,
    d,
    skills_dir,
    llm_client,
    config_dir: str | Path,
) -> str | None:
    """
    레터에서 테마 추출 → 구글 공식 Gemini 이미지 API로 1장 생성 후 저장.
    설정은 config_dir/images.yaml에서 로드(api_key). OS 환경변수 사용 안 함.
    """
    cfg = load_image_config(config_dir)
    if not cfg:
        logger.info("No GOOGLE_API_KEY in .env, skipping card background")
        return None

    theme = extract_theme(letter_md, skills_dir, llm_client, data_dir=data_dir)
    if not theme:
        return None

    out_path = card_bg_image_path(data_dir, d)
    api_key = cfg.get("api_key", "").strip()
    if not api_key:
        return None
    model = cfg.get("model")

    if _generate_gemini_image(theme, api_key, out_path, model=model):
        return f"{d.strftime('%Y%m%d')}.png"
    return None


def update_card_json_bg(data_dir: str, d, bg_filename: str | None) -> None:
    """data/cards/YYYY-MM-DD.json에 bgImage 필드 추가/갱신."""
    from pipeline.storage import card_path
    path = card_path(data_dir, d)
    if not Path(path).is_file():
        return
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    data["bgImage"] = bg_filename
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
