import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app
from src.schemas.memory import MemoryExtractionResult
from src.services.memory_extraction_service import MemoryExtractionGenerationError


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_internal_memory_changes_extract_route_runs_extraction_and_conflict_detection(
    monkeypatch,
    client,
):
    calls = {}

    async def fake_extract_memory_from_confirmed_draft(request):
        calls["extract"] = request
        return MemoryExtractionResult.model_validate(memory_result_payload(conflict=False))

    def fake_detect_memory_conflicts(result, context):
        calls["conflict"] = {
            "result": result,
            "context": context,
        }
        return MemoryExtractionResult.model_validate(memory_result_payload(conflict=True))

    monkeypatch.setattr(
        "src.services.memory_extraction_service.extract_memory_from_confirmed_draft",
        fake_extract_memory_from_confirmed_draft,
    )
    monkeypatch.setattr(
        "src.services.memory_conflict_service.detect_memory_conflicts",
        fake_detect_memory_conflicts,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/memory-changes/extract",
        json={
            "storyId": "story-1",
            "chapterId": "chapter-1",
            "sourceGenerationId": "generation-1",
            "confirmedDraft": "The dream fire marked Lin Jin's palm.",
            "existingMemory": {"timeline": []},
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["storyId"] == "story-1"
    assert data["chapterId"] == "chapter-1"
    assert data["sourceGenerationId"] == "generation-1"
    assert data["changes"][0]["memoryType"] == "timeline"
    assert data["changes"][0]["conflictHints"][0]["severity"] == "warning"
    assert calls["extract"]["confirmedDraft"].startswith("The dream fire")
    assert calls["conflict"]["context"]["existingMemory"] == {"timeline": []}


@pytest.mark.asyncio
async def test_internal_memory_changes_extract_route_maps_input_error(monkeypatch, client):
    async def fake_extract_memory_from_confirmed_draft(request):
        raise MemoryExtractionGenerationError(
            "CONFIRMED_DRAFT_REQUIRED",
            "confirmedDraft is required",
        )

    monkeypatch.setattr(
        "src.services.memory_extraction_service.extract_memory_from_confirmed_draft",
        fake_extract_memory_from_confirmed_draft,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/memory-changes/extract",
        json={
            "storyId": "story-1",
            "chapterId": "chapter-1",
            "sourceGenerationId": "generation-1",
        },
    )

    assert response.status_code == 400
    detail = response.json()["detail"]
    assert detail["code"] == "CONFIRMED_DRAFT_REQUIRED"
    assert detail["storyId"] == "story-1"
    assert detail["chapterId"] == "chapter-1"


@pytest.mark.asyncio
async def test_internal_memory_changes_extract_route_rejects_path_body_mismatch(client):
    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/memory-changes/extract",
        json={
            "storyId": "other-story",
            "chapterId": "chapter-1",
            "sourceGenerationId": "generation-1",
            "confirmedDraft": "The dream fire marked Lin Jin's palm.",
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["code"] == "PATH_BODY_STORY_ID_MISMATCH"


@pytest.mark.asyncio
async def test_internal_memory_changes_extract_route_maps_worker_result_error(monkeypatch, client):
    async def fake_extract_memory_from_confirmed_draft(request):
        raise MemoryExtractionGenerationError(
            "INVALID_MEMORY_EXTRACTION_SCHEMA",
            "Memory extraction response failed schema validation",
        )

    monkeypatch.setattr(
        "src.services.memory_extraction_service.extract_memory_from_confirmed_draft",
        fake_extract_memory_from_confirmed_draft,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/chapters/chapter-1/memory-changes/extract",
        json={
            "storyId": "story-1",
            "chapterId": "chapter-1",
            "sourceGenerationId": "generation-1",
            "confirmedDraft": "The dream fire marked Lin Jin's palm.",
        },
    )

    assert response.status_code == 502
    assert response.json()["detail"]["code"] == "INVALID_MEMORY_EXTRACTION_SCHEMA"


def memory_result_payload(conflict: bool):
    change = {
        "changeId": "timeline-1",
        "memoryType": "timeline",
        "operation": "add",
        "confidence": 0.86,
        "evidence": {
            "quote": "The dream fire marked Lin Jin's palm.",
            "sourceSpan": {
                "startOffset": 0,
                "endOffset": 40,
                "quote": "The dream fire marked Lin Jin's palm.",
            },
        },
        "reasoning": "The mark is a durable event.",
        "blocking": False,
        "conflict": conflict,
        "blockingHints": [],
        "conflictHints": [
            {
                "target": "existing-mark",
                "message": "Possible duplicate of existing timeline memory: existing-mark.",
                "severity": "warning",
            }
        ]
        if conflict
        else [],
        "event": "Dream fire marks Lin Jin",
        "order": 1,
        "timing": "chapter 1",
        "participants": ["Lin Jin"],
        "consequence": "Lin Jin can be tracked by the sect.",
    }
    return {
        "storyId": "story-1",
        "chapterId": "chapter-1",
        "sourceGenerationId": "generation-1",
        "schemaVersion": 1,
        "extractorVersion": "memory-extractor-v1",
        "status": "extracted",
        "summary": "One durable timeline event.",
        "changes": [change],
        "warnings": [],
    }
