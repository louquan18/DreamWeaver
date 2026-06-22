import json

import pytest

from src.schemas.memory import MemoryExtractionResult
from src.services.memory_extraction_service import (
    MemoryExtractionGenerationError,
    build_memory_extraction_messages_from_request,
    extract_memory_from_confirmed_draft,
    parse_memory_extraction_response,
    validate_memory_extraction_request,
)


@pytest.mark.parametrize(
    ("field", "expected_code"),
    [
        ("storyId", "STORY_ID_REQUIRED"),
        ("chapterId", "CHAPTER_ID_REQUIRED"),
        ("sourceGenerationId", "SOURCE_GENERATION_ID_REQUIRED"),
        ("confirmedDraft", "CONFIRMED_DRAFT_REQUIRED"),
    ],
)
def test_validate_memory_extraction_request_rejects_missing_required_fields(
    field,
    expected_code,
):
    payload = memory_extraction_request_payload()
    payload[field] = " "

    with pytest.raises(MemoryExtractionGenerationError) as exc_info:
        validate_memory_extraction_request(payload)

    assert exc_info.value.code == expected_code


def test_validate_memory_extraction_request_rejects_invalid_optional_shapes():
    payload = memory_extraction_request_payload()
    payload["recentChapters"] = {}

    with pytest.raises(MemoryExtractionGenerationError) as exc_info:
        validate_memory_extraction_request(payload)

    assert exc_info.value.code == "INVALID_RECENT_CHAPTERS"


def test_build_memory_extraction_messages_from_request_includes_pipeline_metadata():
    messages = build_memory_extraction_messages_from_request(memory_extraction_request_payload())
    prompt = "\n".join(message["content"] for message in messages)

    assert "Generation metadata:" in prompt
    assert "Review metadata:" in prompt
    assert "Consistency metadata:" in prompt
    assert "Repair metadata:" in prompt
    assert "writer-default" in prompt
    assert "score" in prompt
    assert "mirror-memory-conflict" in prompt
    assert "rewrite-pass-1" in prompt
    assert "Lin Jin confirmed the mirror name in the market." in prompt


def test_parse_memory_extraction_response_accepts_valid_json_object():
    result = parse_memory_extraction_response(json.dumps(valid_memory_result_payload()))

    assert isinstance(result, MemoryExtractionResult)
    assert result.story_id == "story-1"
    assert result.chapter_id == "chapter-1"
    assert result.source_generation_id == "generation-1"
    assert result.changes[0].change_id == "memchg-timeline-1"


def test_parse_memory_extraction_response_accepts_fenced_json_object():
    raw_response = "```json\n" + json.dumps(valid_memory_result_payload()) + "\n```"

    result = parse_memory_extraction_response(raw_response)

    assert result.status == "extracted"
    assert result.summary == "One timeline memory was extracted."


@pytest.mark.parametrize("raw_response", ["", "   ", "```json\n\n```"])
def test_parse_memory_extraction_response_rejects_empty_llm_response(raw_response: str):
    with pytest.raises(MemoryExtractionGenerationError) as exc_info:
        parse_memory_extraction_response(raw_response)

    assert exc_info.value.code == "EMPTY_MEMORY_EXTRACTION_RESPONSE"
    assert "empty" in exc_info.value.message


@pytest.mark.parametrize(
    ("raw_response", "expected_code"),
    [
        ("not json", "INVALID_MEMORY_EXTRACTION_JSON"),
        (json.dumps([]), "INVALID_MEMORY_EXTRACTION_JSON_OBJECT"),
        (
            json.dumps({"storyId": "story-1", "chapterId": "chapter-1"}),
            "INVALID_MEMORY_EXTRACTION_SCHEMA",
        ),
    ],
)
def test_parse_memory_extraction_response_rejects_invalid_output(
    raw_response,
    expected_code,
):
    with pytest.raises(MemoryExtractionGenerationError) as exc_info:
        parse_memory_extraction_response(raw_response)

    assert exc_info.value.code == expected_code


@pytest.mark.asyncio
async def test_extract_memory_from_confirmed_draft_returns_valid_result_from_llm_stream(
    monkeypatch,
):
    captured = {}
    raw_json = json.dumps(valid_memory_result_payload(), ensure_ascii=False)

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
        midpoint = len(raw_json) // 2
        yield raw_json[:midpoint]
        yield raw_json[midpoint:]

    monkeypatch.setattr(
        "src.services.memory_extraction_service.agent_model_chain",
        fake_agent_model_chain,
    )
    monkeypatch.setattr(
        "src.services.memory_extraction_service.agent_temperature",
        fake_agent_temperature,
    )
    monkeypatch.setattr(
        "src.services.memory_extraction_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    result = await extract_memory_from_confirmed_draft(memory_extraction_request_payload())

    assert isinstance(result, MemoryExtractionResult)
    assert result.summary == "One timeline memory was extracted."
    assert captured["agent_type"] == "reviewer"
    assert captured["temperature_agent_type"] == "reviewer"
    assert captured["models"] == ["reviewer-model"]
    assert captured["max_tokens"] == 4096
    assert captured["temperature"] == 0.3
    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert "Lin Jin confirmed the mirror name in the market." in prompt
    assert "writer-default" in prompt


@pytest.mark.asyncio
async def test_extract_memory_from_confirmed_draft_rejects_empty_llm_stream(monkeypatch):
    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        if False:
            yield ""

    monkeypatch.setattr(
        "src.services.memory_extraction_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    with pytest.raises(MemoryExtractionGenerationError) as exc_info:
        await extract_memory_from_confirmed_draft(memory_extraction_request_payload())

    assert exc_info.value.code == "EMPTY_MEMORY_EXTRACTION_RESPONSE"


@pytest.mark.asyncio
async def test_extract_memory_from_confirmed_draft_rejects_result_for_different_generation(
    monkeypatch,
):
    payload = valid_memory_result_payload()
    payload["sourceGenerationId"] = "different-generation"

    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        yield json.dumps(payload, ensure_ascii=False)

    monkeypatch.setattr(
        "src.services.memory_extraction_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    with pytest.raises(MemoryExtractionGenerationError) as exc_info:
        await extract_memory_from_confirmed_draft(memory_extraction_request_payload())

    assert exc_info.value.code == "MEMORY_EXTRACTION_RESULT_MISMATCH"


def memory_extraction_request_payload():
    return {
        "storyId": "story-1",
        "chapterId": "chapter-1",
        "sourceGenerationId": "generation-1",
        "story": {"id": "story-1", "title": "Dream Fire"},
        "chapter": {"id": "chapter-1", "chapterNumber": 3, "title": "The Mirror Market"},
        "blueprint": {
            "premise": "A betrayed disciple follows dream fire.",
            "lockedFacts": [{"text": "Dream fire cannot show complete futures."}],
        },
        "confirmedOutline": {
            "finalOutline": {
                "chapterGoal": "Trace the mirror market clue.",
                "endingHook": "The mirror names the betrayer.",
            }
        },
        "recentChapters": [
            {"chapterNumber": 2, "summary": "Lin Jin escaped the outer sect."}
        ],
        "existingMemory": {
            "timeline": [{"memoryId": "tl-1", "event": "Lin Jin fled the sect."}]
        },
        "generationMetadata": {"modelProfile": "writer-default"},
        "reviewMetadata": {"score": 0.82},
        "consistencyMetadata": {"issues": ["mirror-memory-conflict"]},
        "repairMetadata": {"passId": "rewrite-pass-1"},
        "metadata": {"confirmedBy": "user"},
        "confirmedDraft": (
            "Lin Jin confirmed the mirror name in the market. "
            "The dream fire showed only a fractured symbol."
        ),
    }


def valid_memory_result_payload():
    quote = "Lin Jin confirmed the mirror name in the market."
    return {
        "storyId": "story-1",
        "chapterId": "chapter-1",
        "sourceGenerationId": "generation-1",
        "status": "extracted",
        "summary": "One timeline memory was extracted.",
        "changes": [
            {
                "changeId": "memchg-timeline-1",
                "memoryType": "timeline",
                "operation": "add",
                "confidence": 0.91,
                "evidence": {
                    "quote": quote,
                    "sourceSpan": {
                        "startOffset": 0,
                        "endOffset": len(quote),
                        "quote": quote,
                    },
                },
                "reasoning": "The confirmed draft establishes a durable mirror-market event.",
                "event": "Lin Jin confirms the mirror name in the market.",
                "order": 1,
                "timing": "chapter 3, mirror market scene",
                "participants": ["Lin Jin", "Mirror"],
                "consequence": "Future chapters should treat the mirror name as known.",
            }
        ],
        "warnings": [],
    }
