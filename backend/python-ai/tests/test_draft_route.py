import json

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.schemas.draft import DraftGenerateRequest
from src.services.draft_service import (
    DEFAULT_TARGET_WORDS,
    build_confirmed_outline_draft_messages,
    generate_draft,
    stream_confirmed_outline_draft,
    stream_generate_draft,
    validate_generate_draft_request,
)


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_internal_draft_stream_uses_confirmed_outline(monkeypatch, client):
    async def fake_stream_confirmed_outline_draft(request):
        payload = request.writer_payload()
        assert payload["blueprint"]["premise"] == "A betrayed disciple follows dream fire."
        assert payload["confirmedOutline"]["finalOutline"]["endingHook"] == "The mirror speaks."
        yield "The dream fire "
        yield "obeyed the confirmed outline."

    monkeypatch.setattr(
        "src.services.draft_service.stream_confirmed_outline_draft",
        fake_stream_confirmed_outline_draft,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/stream",
        json=draft_request_payload(),
    )

    assert response.status_code == 200
    body = response.text
    assert "event: node_start" in body
    assert "event: token" in body
    assert "The dream fire" in body
    assert "event: done" in body
    assert "obeyed the confirmed outline" in body
    done_payload = sse_event_data(body, "done")
    assert done_payload == {
        "story_id": "story-1",
        "chapter_id": "chapter-1",
        "generation_id": "generation-1",
        "draft": "The dream fire obeyed the confirmed outline.",
        "word_count": len("The dream fire obeyed the confirmed outline."),
        "tokens_streamed": 2,
    }


@pytest.mark.asyncio
async def test_internal_draft_stream_route_passes_java_confirmed_context(monkeypatch, client):
    captured = {}

    async def fake_stream_generate_draft(request, *, story_id, chapter_id):
        captured["request_type"] = type(request)
        captured["payload"] = request.writer_payload()
        captured["story_id"] = story_id
        captured["chapter_id"] = chapter_id
        yield type(
            "Event",
            (),
            {"event": "done", "data": {"draft": "route ok", "tokens_streamed": 0}},
        )()

    monkeypatch.setattr(
        "src.api.routes.drafts.stream_generate_draft",
        fake_stream_generate_draft,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/stream",
        json=draft_request_payload(),
    )

    assert response.status_code == 200
    assert "route ok" in response.text
    assert captured["request_type"] is DraftGenerateRequest
    assert captured["story_id"] == "story-1"
    assert captured["chapter_id"] == "chapter-1"
    assert captured["payload"]["blueprint"]["lockedFacts"][0]["text"] == (
        "Dream fire cannot show complete futures"
    )
    assert captured["payload"]["confirmedOutline"]["finalOutline"]["endingHook"] == (
        "The mirror speaks."
    )
    assert captured["payload"]["characters"][0]["name"] == "Lin Jin"
    assert captured["payload"]["foreshadows"][0]["status"] == "triggered"


@pytest.mark.asyncio
async def test_internal_draft_stream_rejects_missing_confirmed_outline(client):
    payload = draft_request_payload()
    payload["confirmedOutline"] = {}

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/stream",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIRMED_OUTLINE_REQUIRED"


@pytest.mark.asyncio
async def test_internal_draft_stream_rejects_missing_final_outline(client):
    payload = draft_request_payload()
    payload["confirmedOutline"] = {"id": "outline-1"}

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/stream",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIRMED_FINAL_OUTLINE_REQUIRED"


@pytest.mark.asyncio
async def test_internal_draft_stream_rejects_missing_blueprint(client):
    payload = draft_request_payload()
    payload["blueprint"] = {}

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/stream",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "CONFIRMED_BLUEPRINT_REQUIRED"


@pytest.mark.parametrize(
    ("field", "expected_code"),
    [
        ("generationId", "GENERATION_ID_REQUIRED"),
        ("story", "STORY_REQUIRED"),
        ("chapter", "CHAPTER_REQUIRED"),
    ],
)
@pytest.mark.asyncio
async def test_internal_draft_stream_rejects_missing_required_context(
    field,
    expected_code,
    client,
):
    payload = draft_request_payload()
    payload[field] = "" if field == "generationId" else {}

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/stream",
        json=payload,
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == expected_code


def test_validate_generate_draft_request_returns_task_schema():
    request = validate_generate_draft_request(draft_request_payload())

    assert isinstance(request, DraftGenerateRequest)
    assert request.generation_id == "generation-1"
    assert request.target_words == 1800
    assert request.writer_payload()["confirmedOutline"]["finalOutline"]["endingHook"] == (
        "The mirror speaks."
    )
    assert request.writer_payload()["timeline"][0]["event"] == "Lin Jin escaped the outer sect."
    assert request.writer_payload()["characters"][0]["name"] == "Lin Jin"
    assert request.writer_payload()["contextMetadata"]["policy"] == "structured-memory-v1"


def test_validate_generate_draft_request_defaults_structured_memory_fields():
    payload = draft_request_payload()
    for field in (
        "timeline",
        "characters",
        "world",
        "foreshadows",
        "additionalMemory",
        "contextMetadata",
    ):
        payload.pop(field)

    request = validate_generate_draft_request(payload)
    payload = request.writer_payload()

    assert payload["timeline"] == []
    assert payload["characters"] == []
    assert payload["world"] == []
    assert payload["foreshadows"] == []
    assert payload["additionalMemory"] == []
    assert payload["contextMetadata"] == {}


def test_confirmed_outline_draft_prompt_contains_blueprint_and_outline():
    messages = build_confirmed_outline_draft_messages(draft_request_payload())
    prompt = "\n".join(message["content"] for message in messages)

    assert "不得调用或模拟 Planner" in prompt
    assert "confirmedOutline.finalOutline" in prompt
    assert "A betrayed disciple follows dream fire." in prompt
    assert "Dream fire cannot show complete futures" in prompt
    assert "Trace the hidden mirror through the market." in prompt
    assert "The token burns near a mirror stall." in prompt
    assert "The mirror speaks." in prompt
    assert "Keep the ending quiet and ominous." in prompt
    assert "[structuredTimeline]" in prompt
    assert "Lin Jin escaped the outer sect." in prompt
    assert "[characterStates]" in prompt
    assert "injured but carrying the dream token" in prompt
    assert "[worldFacts]" in prompt
    assert "Mirror fire cannot cross locked gates." in prompt
    assert "[openForeshadows]" in prompt
    assert "The mirror token is burning." in prompt
    assert "confirmedOutline > blueprint.lockedFacts > structured memory" in prompt
    assert "If recentChapters conflict with structured memory" in prompt
    assert "additionalMemory is supplemental retrieval material" in prompt
    assert "must not override confirmedOutline" in prompt
    assert "Recent chapter compression rules" in prompt
    assert 'contextRole="recent_full_text"' in prompt
    assert 'contextRole="recent_summary"' in prompt


def test_confirmed_outline_draft_prompt_defaults_to_about_2000_words():
    payload = draft_request_payload()
    payload.pop("targetWords")

    request = validate_generate_draft_request(payload)
    messages = build_confirmed_outline_draft_messages(request)
    prompt = "\n".join(message["content"] for message in messages)

    assert request.target_words == DEFAULT_TARGET_WORDS
    assert f"约 {DEFAULT_TARGET_WORDS} 字" in prompt
    assert "不要写成短梗概" in prompt


def test_confirmed_outline_draft_prompt_defaults_when_target_words_is_null():
    payload = draft_request_payload()
    payload["targetWords"] = None

    request = validate_generate_draft_request(payload)

    assert request.target_words == DEFAULT_TARGET_WORDS


@pytest.mark.asyncio
async def test_confirmed_outline_draft_stream_uses_writer_model_not_planner(monkeypatch):
    captured = {}

    def fake_agent_model_chain(agent_type):
        captured["agent_type"] = agent_type
        return ["draft-model"]

    def fake_agent_temperature(agent_type):
        captured["temperature_agent_type"] = agent_type
        return 0.8

    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        captured["messages"] = messages
        captured["models"] = models
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        yield "正文"

    monkeypatch.setattr("src.services.draft_service.agent_model_chain", fake_agent_model_chain)
    monkeypatch.setattr("src.services.draft_service.agent_temperature", fake_agent_temperature)
    monkeypatch.setattr(
        "src.services.draft_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    tokens = [token async for token in stream_confirmed_outline_draft(draft_request_payload())]

    assert tokens == ["正文"]
    assert captured["agent_type"] == "draft"
    assert captured["temperature_agent_type"] == "draft"
    assert captured["models"] == ["draft-model"]
    assert captured["max_tokens"] >= 4096
    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert "不得调用或模拟 Planner" in prompt
    assert "The mirror speaks." in prompt


@pytest.mark.asyncio
async def test_stream_generate_draft_emits_stable_task_events(monkeypatch):
    async def fake_stream_confirmed_outline_draft(request):
        yield "first "
        yield "second"

    monkeypatch.setattr(
        "src.services.draft_service.stream_confirmed_outline_draft",
        fake_stream_confirmed_outline_draft,
    )

    events = [
        event
        async for event in stream_generate_draft(
            draft_request_payload(),
            story_id="story-1",
            chapter_id="chapter-1",
        )
    ]

    assert [event.event for event in events] == ["node_start", "token", "token", "node_end", "done"]
    assert events[-1].data == {
        "story_id": "story-1",
        "chapter_id": "chapter-1",
        "generation_id": "generation-1",
        "draft": "first second",
        "word_count": len("first second"),
        "tokens_streamed": 2,
    }


@pytest.mark.asyncio
async def test_generate_draft_collects_tokens_into_result(monkeypatch):
    async def fake_stream_confirmed_outline_draft(request):
        yield "正文"
        yield "完成"

    monkeypatch.setattr(
        "src.services.draft_service.stream_confirmed_outline_draft",
        fake_stream_confirmed_outline_draft,
    )

    result = await generate_draft(
        draft_request_payload(),
        story_id="story-1",
        chapter_id="chapter-1",
    )

    assert result.sse_payload() == {
        "story_id": "story-1",
        "chapter_id": "chapter-1",
        "generation_id": "generation-1",
        "draft": "正文完成",
        "word_count": len("正文完成"),
        "tokens_streamed": 2,
    }


def draft_request_payload():
    return {
        "generationId": "generation-1",
        "userId": "user-1",
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
        "timeline": [
            {
                "id": "tl-1",
                "event": "Lin Jin escaped the outer sect.",
                "importance": "high",
            }
        ],
        "characters": [
            {
                "name": "Lin Jin",
                "state": "injured but carrying the dream token",
                "location": "mirror market",
            }
        ],
        "world": [
            {
                "subject": "Mirror fire",
                "description": "Mirror fire cannot cross locked gates.",
                "locked": True,
            }
        ],
        "foreshadows": [
            {
                "id": "fs-1",
                "status": "triggered",
                "content": "The mirror token is burning.",
                "needsAttention": True,
            }
        ],
        "additionalMemory": [],
        "contextMetadata": {
            "policy": "structured-memory-v1",
            "limits": {
                "timeline": 20,
                "characters": 12,
                "world": 20,
                "foreshadows": 10,
            },
        },
        "extraPrompt": "Keep the ending quiet and ominous.",
        "targetWords": 1800,
        "modelProfile": "writing",
    }


def sse_event_data(body: str, event_name: str):
    blocks = [block for block in body.split("\n\n") if block.strip()]
    for block in blocks:
        lines = block.splitlines()
        if f"event: {event_name}" not in lines:
            continue
        data_line = next(line for line in lines if line.startswith("data: "))
        return json.loads(data_line.removeprefix("data: "))
    raise AssertionError(f"SSE event not found: {event_name}")
