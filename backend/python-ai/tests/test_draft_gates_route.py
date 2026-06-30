import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.services.consistency_service import ConsistencyCheckError
from src.services.review_service import ReviewGenerationError


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_consistency_gate_route_returns_report(monkeypatch, client):
    captured = {}

    async def fake_check_consistency(request):
        captured["request"] = request
        return type(
            "Report",
            (),
            {
                "model_dump": lambda self, by_alias: {
                    "summary": "No consistency issues.",
                    "issues": [],
                    "checkedRuleIds": ["WORLD_LOCKED_FACT"],
                    "passedRuleIds": ["WORLD_LOCKED_FACT"],
                    "blocking": False,
                    "autoRepairRequired": False,
                }
            },
        )()

    monkeypatch.setattr("src.api.routes.draft_gates.check_consistency", fake_check_consistency)

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/consistency",
        json=gate_request_payload(),
    )

    assert response.status_code == 200
    assert response.json()["checkedRuleIds"] == ["WORLD_LOCKED_FACT"]
    assert captured["request"]["generationId"] == "generation-1"


@pytest.mark.asyncio
async def test_review_gate_route_returns_report(monkeypatch, client):
    async def fake_review_quality(request):
        return type(
            "Report",
            (),
            {
                "model_dump": lambda self, by_alias: {
                    "overallScore": 88,
                    "summary": "Draft is ready.",
                    "issues": [],
                    "blocking": False,
                    "autoRepairRequired": False,
                    "revisionHints": [],
                    "strengths": ["Clear ending hook"],
                }
            },
        )()

    monkeypatch.setattr("src.api.routes.draft_gates.review_quality", fake_review_quality)

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/review",
        json=gate_request_payload(),
    )

    assert response.status_code == 200
    assert response.json()["overallScore"] == 88


@pytest.mark.asyncio
async def test_consistency_gate_route_maps_input_errors(monkeypatch, client):
    async def fake_check_consistency(request):
        raise ConsistencyCheckError("DRAFT_REQUIRED", "draft is required")

    monkeypatch.setattr("src.api.routes.draft_gates.check_consistency", fake_check_consistency)

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/consistency",
        json=gate_request_payload(),
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "DRAFT_REQUIRED"


@pytest.mark.asyncio
async def test_review_gate_route_maps_worker_errors(monkeypatch, client):
    async def fake_review_quality(request):
        raise ReviewGenerationError("REVIEW_MODEL_ERROR", "model failed")

    monkeypatch.setattr("src.api.routes.draft_gates.review_quality", fake_review_quality)

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/drafts/review",
        json=gate_request_payload(),
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "REVIEW_MODEL_ERROR"


def gate_request_payload():
    return {
        "generationId": "generation-1",
        "story": {"title": "Dream Fire"},
        "chapter": {"title": "The Mirror Market"},
        "blueprint": {"premise": "A betrayed disciple follows dream fire."},
        "confirmedOutline": {
            "finalOutline": {
                "chapterGoal": "Trace the mirror token.",
                "endingHook": "The mirror speaks.",
            }
        },
        "recentChapters": [],
        "timeline": [],
        "characters": [],
        "worldState": [],
        "activeForeshadows": [],
        "draft": "The mirror speaks at the ending.",
    }
