"""Topical relevance gate for the daily agentic AI newsletter."""
from __future__ import annotations

import re
from typing import Iterable

CATEGORY_AGENTIC = "에이전틱 코딩 & 프론티어 모델"
CATEGORY_INFRA = "GitHub & 인프라 트렌드"
CATEGORY_AX = "산업별 AX"
CATEGORY_KOREA = "대한민국 IT"

AI_RE = re.compile(
    r"(?<![a-z0-9])("
    r"ai|a\.i\.|llm|llms|gpt-?\d*|chatgpt|openai|anthropic|claude|gemini|"
    r"deepseek|grok|xai|mistral|llama|qwen|machine learning|deep learning|"
    r"neural|large language model|foundation model|frontier model|generative ai|"
    r"genai|chatbot"
    r")(?![a-z0-9])"
    r"|인공지능|생성형|머신러닝|딥러닝|신경망|챗봇|언어모델",
    re.IGNORECASE,
)

AGENTIC_CODE_RE = re.compile(
    r"(?<![a-z0-9])("
    r"agentic|agent|agents|coding agent|code agent|codex|cursor|claude code|"
    r"copilot|devin|windsurf|composer|roo code|cline|mcp|tool calling|"
    r"function calling|context window|vibe coding|vibe code|codegen|"
    r"prompt engineering|prompt"
    r")(?![a-z0-9])"
    r"|에이전틱|에이전트|코딩 에이전트|개발 에이전트|코덱스|코파일럿|"
    r"컨텍스트|프롬프트|도구 호출|코드 생성",
    re.IGNORECASE,
)

DEV_TOOL_RE = re.compile(
    r"(?<![a-z0-9])("
    r"github|gitlab|vscode|vs code|visual studio code|ide|ci/cd|ci|cd|sdk|api|"
    r"cli|terminal|repo|repository|pull request|commit|telemetry|open source|"
    r"opensource|wasm|webassembly"
    r")(?![a-z0-9])"
    r"|깃허브|오픈소스|커밋|레포|저장소|텔레메트리|개발자|인프라|도구|"
    r"웹어셈블리",
    re.IGNORECASE,
)

INDUSTRY_RE = re.compile(
    r"(?<![a-z0-9])("
    r"travel|finance|manufacturing|healthcare|education|retail|commerce|"
    r"automotive|vehicle|robot|robotics|public sector|government|legal|"
    r"insurance|bank|airline|hospital|hiring|recruiting|autonomous vehicle|"
    r"self-driving|fsd|tesla"
    r")(?![a-z0-9])"
    r"|트래블|여행|금융|제조|의료|병원|헬스케어|교육|리테일|커머스|"
    r"자동차|차량|자율주행|무인차|로봇|정부|공공|법률|보험|은행|항공|채용",
    re.IGNORECASE,
)

AUTOMATION_RE = re.compile(
    r"(?<![a-z0-9])("
    r"autonomous|self-driving|robot|robotics|automation|automated|algorithmic|"
    r"fsd"
    r")(?![a-z0-9])"
    r"|자율주행|무인차|로봇|자동화|알고리듬|알고리즘|자율",
    re.IGNORECASE,
)


def _item_text(item: dict, *, include_summary: bool) -> str:
    fields = ("title", "source_id", "source", "url")
    if include_summary:
        fields = ("title", "summary", "source_id", "source", "url")
    return " ".join(str(item.get(field) or "") for field in fields)


def is_relevant_item(item: dict) -> bool:
    """Return True when an item fits the agentic AI/code newsletter scope."""
    if not isinstance(item, dict):
        return False

    primary_text = _item_text(item, include_summary=False)
    full_text = _item_text(item, include_summary=True)
    category = str(item.get("category") or "")
    has_ai = bool(AI_RE.search(primary_text))
    has_agentic_code = bool(AGENTIC_CODE_RE.search(primary_text))
    has_dev_tool = bool(DEV_TOOL_RE.search(primary_text))
    has_industry = bool(INDUSTRY_RE.search(primary_text))
    has_automation = bool(AUTOMATION_RE.search(primary_text))

    # Summary is model-produced after analyze, so treat it only as supporting
    # context. It can confirm a primary-source signal, but not create one.
    full_has_ai = bool(AI_RE.search(full_text))
    full_has_agentic_code = bool(AGENTIC_CODE_RE.search(full_text))
    full_has_dev_tool = bool(DEV_TOOL_RE.search(full_text))
    full_has_industry = bool(INDUSTRY_RE.search(full_text))
    full_has_automation = bool(AUTOMATION_RE.search(full_text))

    if CATEGORY_AX in category:
        return has_industry and (has_ai or has_automation or has_agentic_code)
    if CATEGORY_INFRA in category:
        return has_agentic_code or (has_ai and has_dev_tool)
    if CATEGORY_AGENTIC in category:
        return has_agentic_code or has_ai
    if CATEGORY_KOREA in category:
        return has_agentic_code or has_ai or (has_dev_tool and has_ai)

    has_primary_signal = has_agentic_code or has_ai or has_automation
    has_supporting_context = (
        full_has_agentic_code
        or full_has_ai
        or full_has_automation
        or full_has_dev_tool
        or full_has_industry
    )
    return has_primary_signal and has_supporting_context


def filter_relevant_items(items: Iterable[dict]) -> list[dict]:
    """Drop off-topic items instead of forcing them into a weak category."""
    return [item for item in items if is_relevant_item(item)]
