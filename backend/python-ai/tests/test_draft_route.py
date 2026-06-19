import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.services.draft_service import build_confirmed_outline_draft_messages


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_internal_draft_stream_uses_confirmed_outline(monkeypatch, client):
    async def fake_stream_confirmed_outline_draft(request):
        assert request["blueprint"]["premise"] == "A betrayed disciple follows dream fire."
        assert request["confirmedOutline"]["finalOutline"]["endingHook"] == "The mirror speaks."
        yield "The dream fire "
        yield "obeyed the confirmed outline."

    monkeypatch.setattr(
        "src.api.routes.drafts.stream_confirmed_outline_draft",
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


def test_confirmed_outline_draft_prompt_contains_blueprint_and_outline():
    messages = build_confirmed_outline_draft_messages(draft_request_payload())
    prompt = "\n".join(message["content"] for message in messages)

    assert "不得重新规划" in prompt
    assert "A betrayed disciple follows dream fire." in prompt
    assert "Dream fire cannot show complete futures" in prompt
    assert "Trace the hidden mirror through the market." in prompt
    assert "The mirror speaks." in prompt
    assert "Keep the ending quiet and ominous." in prompt


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
        "extraPrompt": "Keep the ending quiet and ominous.",
        "targetWords": 1800,
        "modelProfile": "writing",
    }
