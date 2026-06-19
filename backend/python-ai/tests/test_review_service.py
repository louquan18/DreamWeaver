import json

import pytest

from src.schemas.review import DraftQualityReviewReport
from src.services.review_service import (
    ReviewGenerationError,
    build_review_quality_messages,
    parse_review_quality_response,
    review_quality,
    validate_review_quality_request,
)


def test_review_quality_prompt_contains_blueprint_outline_and_draft():
    messages = build_review_quality_messages(review_request_payload())
    prompt = "\n".join(message["content"] for message in messages)

    assert "confirmedOutline" in prompt
    assert "finalOutline" in prompt
    assert "A betrayed disciple follows dream fire." in prompt
    assert "Dream fire cannot show complete futures" in prompt
    assert "Trace the hidden mirror through the market." in prompt
    assert "The mirror speaks." in prompt
    assert "Lin Jin followed the dream fire into the mirror market." in prompt
    assert "Keep the ending quiet and ominous." in prompt


@pytest.mark.asyncio
async def test_review_quality_returns_valid_report_from_llm_json(monkeypatch):
    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        yield json.dumps(valid_review_json())

    monkeypatch.setattr(
        "src.services.review_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    report = await review_quality(review_request_payload())

    assert isinstance(report, DraftQualityReviewReport)
    assert report.overall_score == 86
    assert report.summary == "Draft follows the outline with only minor pacing concerns."
    assert report.issues[0].severity == "P2"
    assert report.model_dump(by_alias=True)["overallScore"] == 86
    assert "revision_hints" not in report.model_dump(by_alias=True)


def test_parse_review_quality_response_p0_forces_blocking_gate():
    raw_response = json.dumps(
        {
            "overallScore": 38,
            "summary": "Draft breaks a locked fact.",
            "issues": [
                {
                    "severity": "P0",
                    "category": "world",
                    "message": "Dream fire reveals a complete future.",
                    "evidence": "The draft says the flame showed every event of tomorrow.",
                    "suggestion": "Rewrite the vision so it is partial and ambiguous.",
                    "blocking": False,
                    "autoRepairRequired": False,
                }
            ],
            "blocking": False,
            "autoRepairRequired": False,
        }
    )

    report = parse_review_quality_response(raw_response)

    assert report.blocking is True
    assert report.auto_repair_required is True
    assert report.issues[0].blocking is True
    assert report.issues[0].auto_repair_required is True


def test_parse_review_quality_response_rejects_invalid_json():
    with pytest.raises(ReviewGenerationError) as exc_info:
        parse_review_quality_response("not json")

    assert exc_info.value.code == "INVALID_REVIEW_JSON"


def test_parse_review_quality_response_rejects_invalid_schema():
    with pytest.raises(ReviewGenerationError) as exc_info:
        parse_review_quality_response(json.dumps({"overallScore": 120, "summary": ""}))

    assert exc_info.value.code == "INVALID_REVIEW_SCHEMA"


@pytest.mark.asyncio
async def test_review_quality_uses_reviewer_model_not_writer_or_planner(monkeypatch):
    captured = {}

    def fake_agent_model_chain(agent_type):
        captured["agent_type"] = agent_type
        return ["reviewer-model"]

    def fake_agent_temperature(agent_type):
        captured["temperature_agent_type"] = agent_type
        return 0.3

    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        captured["messages"] = messages
        captured["models"] = models
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        yield json.dumps(valid_review_json())

    monkeypatch.setattr("src.services.review_service.agent_model_chain", fake_agent_model_chain)
    monkeypatch.setattr("src.services.review_service.agent_temperature", fake_agent_temperature)
    monkeypatch.setattr(
        "src.services.review_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    report = await review_quality(review_request_payload())

    assert report.overall_score == 86
    assert captured["agent_type"] == "reviewer"
    assert captured["temperature_agent_type"] == "reviewer"
    assert captured["models"] == ["reviewer-model"]
    assert captured["max_tokens"] == 4096
    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert "Lin Jin followed the dream fire into the mirror market." in prompt
    assert "planner" not in captured["agent_type"]
    assert "writer" not in captured["agent_type"]


@pytest.mark.parametrize(
    ("field", "expected_code"),
    [
        ("generationId", "GENERATION_ID_REQUIRED"),
        ("story", "STORY_REQUIRED"),
        ("chapter", "CHAPTER_REQUIRED"),
        ("blueprint", "CONFIRMED_BLUEPRINT_REQUIRED"),
        ("confirmedOutline", "CONFIRMED_OUTLINE_REQUIRED"),
        ("draft", "DRAFT_REQUIRED"),
    ],
)
def test_validate_review_quality_request_rejects_missing_required_context(
    field,
    expected_code,
):
    payload = review_request_payload()
    payload[field] = "" if field in {"generationId", "draft"} else {}

    with pytest.raises(ReviewGenerationError) as exc_info:
        validate_review_quality_request(payload)

    assert exc_info.value.code == expected_code


def test_validate_review_quality_request_rejects_missing_final_outline():
    payload = review_request_payload()
    payload["confirmedOutline"] = {"id": "outline-1"}

    with pytest.raises(ReviewGenerationError) as exc_info:
        validate_review_quality_request(payload)

    assert exc_info.value.code == "CONFIRMED_FINAL_OUTLINE_REQUIRED"


def valid_review_json():
    return {
        "overallScore": 86,
        "summary": "Draft follows the outline with only minor pacing concerns.",
        "issues": [
            {
                "severity": "P2",
                "category": "pacing",
                "message": "The market search resolves a little quickly.",
                "evidence": "The mirror stall is found immediately after entering the market.",
                "suggestion": "Add one short obstacle before the mirror stall.",
                "sceneIndex": 1,
            }
        ],
        "blocking": False,
        "autoRepairRequired": False,
        "revisionHints": ["Add a small misdirection before the mirror speaks."],
        "strengths": ["The ending hook matches the confirmed outline."],
    }


def review_request_payload():
    return {
        "generationId": "generation-1",
        "story": {
            "id": "story-1",
            "title": "Dream Fire",
            "genre": "xianxia",
        },
        "chapter": {
            "id": "chapter-1",
            "chapterNumber": 3,
            "title": "The Mirror Market",
        },
        "blueprint": {
            "premise": "A betrayed disciple follows dream fire.",
            "genre": "xianxia",
            "tone": "tense and lyrical",
            "protagonist": {"name": "Lin Jin"},
            "mainThread": {"goal": "Find the source of dream fire"},
            "coreConflict": {"external": "Sect hunters close in"},
            "worldSeed": {"rules": ["Dream fire cannot show complete futures"]},
            "lockedFacts": [{"text": "Dream fire cannot show complete futures"}],
        },
        "confirmedOutline": {
            "id": "outline-1",
            "finalOutline": {
                "chapterGoal": "Trace the hidden mirror through the market.",
                "sceneOutline": [
                    {"order": 1, "summary": "Lin Jin enters the market under a false name."},
                    {"order": 2, "summary": "The token burns near a mirror stall."},
                    {"order": 3, "summary": "A reflection names the betrayer."},
                ],
                "endingHook": "The mirror speaks.",
            },
        },
        "recentChapters": [
            {
                "chapterNumber": 2,
                "title": "Ash Road",
                "content": "Lin Jin escaped the outer sect with the dream token.",
            }
        ],
        "extraPrompt": "Keep the ending quiet and ominous.",
        "targetWords": 1800,
        "draft": (
            "Lin Jin followed the dream fire into the mirror market. "
            "The token burned near a silver stall, and the mirror spoke."
        ),
    }
