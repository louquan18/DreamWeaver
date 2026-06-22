import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.schemas.outline import ChapterOutlineOptionsDraft
from src.services.outline_service import OutlineGenerationError


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_internal_outline_options_generate_route(monkeypatch, client):
    async def fake_generate_outline_options(**kwargs):
        return ChapterOutlineOptionsDraft.model_validate(
            outline_options_payload(
                kwargs["story_id"],
                kwargs["chapter_id"],
                kwargs["option_group_id"],
            )
        )

    monkeypatch.setattr(
        "src.api.routes.outlines.generate_outline_options",
        fake_generate_outline_options,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/outline-options/generate",
        json={
            "optionGroupId": "group-1",
            "authorIntent": {"goal": "open with pressure"},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["storyId"] == "story-1"
    assert data["chapterId"] == "chapter-1"
    assert data["optionGroupId"] == "group-1"
    assert [option["optionCode"] for option in data["options"]] == ["A", "B", "C"]


@pytest.mark.asyncio
async def test_internal_outline_options_generate_route_maps_generation_error(monkeypatch, client):
    async def fake_generate_outline_options(**kwargs):
        raise OutlineGenerationError("outline options must include exactly A, B, and C")

    monkeypatch.setattr(
        "src.api.routes.outlines.generate_outline_options",
        fake_generate_outline_options,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/outline-options/generate",
        json={"optionGroupId": "group-1"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "OUTLINE_GENERATION_ERROR"
    assert detail["storyId"] == "story-1"
    assert "A, B, and C" in detail["message"]


@pytest.mark.asyncio
async def test_internal_outline_options_generate_route_rejects_missing_option_group_id(
    monkeypatch,
    client,
):
    async def fake_generate_outline_options(**kwargs):
        pytest.fail("outline generator should not run without optionGroupId")

    monkeypatch.setattr(
        "src.api.routes.outlines.generate_outline_options",
        fake_generate_outline_options,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/outline-options/generate",
        json={
            "authorIntent": {"goal": "open with pressure"},
            "blueprint": {"premise": "A betrayed disciple follows dream fire."},
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "OPTION_GROUP_ID_REQUIRED"
    assert detail["storyId"] == "story-1"
    assert detail["chapterId"] == "chapter-1"


def outline_options_payload(story_id: str, chapter_id: str, option_group_id: str):
    return {
        "storyId": story_id,
        "chapterId": chapter_id,
        "optionGroupId": option_group_id,
        "options": [
            option_payload(story_id, chapter_id, option_group_id, "A", "steady"),
            option_payload(story_id, chapter_id, option_group_id, "B", "conflict"),
            option_payload(story_id, chapter_id, option_group_id, "C", "foreshadow"),
        ],
    }


def option_payload(story_id: str, chapter_id: str, group_id: str, code: str, option_type: str):
    return {
        "storyId": story_id,
        "chapterId": chapter_id,
        "optionGroupId": group_id,
        "optionCode": code,
        "optionType": option_type,
        "titleCandidates": [f"Route {code}"],
        "chapterGoal": f"Advance route {code}",
        "storySummary": f"Route {code} pressure rises.",
        "sceneOutline": [
            {"order": 1, "summary": "Open", "purpose": "setup", "outcome": "clue"},
            {"order": 2, "summary": "Turn", "purpose": "pressure", "outcome": "choice"},
            {"order": 3, "summary": "Hook", "purpose": "payoff", "outcome": "danger"},
        ],
        "charactersInvolved": [{"name": "Ming", "motivation": "survive"}],
        "conflict": {"stakes": "loss of the gate"},
        "highlightMoment": "The seal burns.",
        "foreshadowActions": [
            {
                "action": "plant",
                "description": "A hidden seal reacts.",
                "payoffHint": "The seal returns later.",
            }
        ]
        if code == "C"
        else [],
        "memoryReferences": [],
        "whyThisPlan": f"Route {code} has a distinct job.",
        "endingHook": "A voice speaks an old name.",
        "riskNotes": [],
        "status": "generated",
    }
