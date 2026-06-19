import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.schemas.blueprint import BlueprintValidationIssue, NovelBlueprintDraft
from src.services.blueprint_validation import BlueprintValidationError


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_internal_blueprint_generate_route(monkeypatch, client):
    async def fake_generate_light_blueprint(story_id, request):
        return NovelBlueprintDraft(
            story_id=story_id,
            source_prompt=request.source_prompt,
            premise="A betrayed disciple survives and seeks the truth.",
            genre=request.genre,
            tone=request.tone,
            protagonist={"name": "Lin Yan", "initialGoal": "revenge"},
            main_thread={"goal": "take revenge and reveal the dream mirror source"},
            core_conflict={"external": "sect pursuit", "stakes": "loss of freedom"},
            world_seed={"rules": []},
            writing_preferences={"pace": "fast"},
            locked_facts=[
                {
                    "id": "fact-001",
                    "text": "Dream prophecy only reveals fragments",
                    "category": "world",
                    "source": "agent",
                }
            ],
        )

    monkeypatch.setattr(
        "src.api.routes.blueprints.generate_light_blueprint",
        fake_generate_light_blueprint,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/blueprints/generate",
        json={
            "sourcePrompt": "A betrayed disciple uses dream prophecy for revenge",
            "genre": "xianxia",
            "tone": "fast",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["storyId"] == "story-1"
    assert data["sourcePrompt"].startswith("A betrayed disciple")
    assert data["mainThread"]["goal"] == "take revenge and reveal the dream mirror source"
    assert data["lockedFacts"][0]["text"] == "Dream prophecy only reveals fragments"


@pytest.mark.asyncio
async def test_internal_blueprint_generate_route_maps_validation_error(monkeypatch, client):
    async def fake_generate_light_blueprint(story_id, request):
        raise BlueprintValidationError(
            [
                BlueprintValidationIssue(
                    code="REQUIRED_FIELD_MISSING",
                    path="protagonist.name",
                    message="protagonist.name must not be empty",
                    severity="error",
                    blocking=True,
                )
            ]
        )

    monkeypatch.setattr(
        "src.api.routes.blueprints.generate_light_blueprint",
        fake_generate_light_blueprint,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/blueprints/generate",
        json={"sourcePrompt": "A betrayed disciple seeks revenge"},
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "VALIDATION_ERROR"
    assert detail["issues"][0]["path"] == "protagonist.name"
