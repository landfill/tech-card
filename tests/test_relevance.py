from pipeline.relevance import filter_relevant_items, is_relevant_item


def test_filter_drops_forced_industry_ax_noise():
    items = [
        {
            "title": "Three cruise ship passengers die in suspected hantavirus outbreak",
            "summary": "Reuters health emergency report.",
            "category": "산업별 AX",
        },
        {
            "title": "Let's Buy Spirit Air",
            "summary": "Campaign page for an airline.",
            "category": "산업별 AX",
        },
        {
            "title": "Tesla FSD false advertising ruling",
            "summary": "A self-driving product responsibility case involving autonomous vehicles.",
            "category": "산업별 AX",
        },
        {
            "title": "알고리듬 채용에서의 AI 자기선호",
            "summary": "LLM이 이력서 생성 및 평가에 사용될 때의 채용 편향 연구.",
            "category": "산업별 AX",
        },
    ]

    kept = filter_relevant_items(items)

    assert [item["title"] for item in kept] == [
        "Tesla FSD false advertising ruling",
        "알고리듬 채용에서의 AI 자기선호",
    ]


def test_filter_requires_ai_tie_for_github_infra():
    assert is_relevant_item(
        {
            "title": "VS Code inserts Co-Authored-by Copilot",
            "summary": "The IDE changes metadata for AI-generated contributions.",
            "category": "GitHub & 인프라 트렌드",
        }
    )
    assert not is_relevant_item(
        {
            "title": "PEP 661 sentinel values approved",
            "summary": "A Python language proposal for sentinel() values.",
            "category": "GitHub & 인프라 트렌드",
        }
    )
    assert not is_relevant_item(
        {
            "title": "WAH: single-header WebAssembly interpreter",
            "summary": "A small WASM runtime implementation.",
            "category": "GitHub & 인프라 트렌드",
        }
    )
    assert not is_relevant_item(
        {
            "title": "Show HN: Optical Design and Simulation in Matlab",
            "summary": "The generated summary speculates that an agent could explore the API.",
            "category": "GitHub & 인프라 트렌드",
        }
    )


def test_filter_keeps_agentic_coding_tools():
    items = [
        {
            "title": "CTX for Claude Code sessions",
            "summary": "Preserves context across AI coding agent sessions.",
            "category": "에이전틱 코딩 & 프론티어 모델",
        },
        {
            "title": "obscura: headless browser for AI agents",
            "summary": "A headless browser for AI agents and web scraping.",
            "category": "에이전틱 코딩 & 프론티어 모델",
        },
        {
            "title": "Conclave: make LLMs debate before responding",
            "summary": "A debate pattern for model answers.",
            "category": "에이전틱 코딩 & 프론티어 모델",
        },
    ]

    assert filter_relevant_items(items) == items


def test_ascii_ai_does_not_match_air():
    assert not is_relevant_item(
        {
            "title": "Let's Buy Spirit Air",
            "summary": "Airline campaign page.",
            "category": "산업별 AX",
        }
    )
