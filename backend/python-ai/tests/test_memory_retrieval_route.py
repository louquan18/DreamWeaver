import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.mark.asyncio
async def test_vector_search_returns_bounded_results(monkeypatch, client):
    async def fake_paragraphs(story_id, query, k=5, chapter_range=None):
        return [
            {
                "chapter_number": index,
                "paragraph_index": index,
                "text": f"paragraph {index} mirror oath",
                "distance": 0.1,
            }
            for index in range(10)
        ]

    async def fake_summaries(story_id, query, k=5):
        return [
            {
                "chapter_number": 99,
                "summary": "summary mirror oath",
                "distance": 0.2,
            }
        ]

    monkeypatch.setattr(
        "src.api.routes.memory_retrieval.search_relevant_paragraphs",
        fake_paragraphs,
    )
    monkeypatch.setattr(
        "src.api.routes.memory_retrieval.search_relevant_chapters",
        fake_summaries,
    )

    response = await client.post(
        "/internal/ai/stories/story-1/memory/retrieve",
        json={"query": "mirror oath", "k": 3},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["retrievalMethod"] == "vector"
    assert len(payload["additionalMemory"]) == 3
    assert payload["additionalMemory"][0]["type"] == "paragraph"
    assert payload["additionalMemory"][0]["retrievalMethod"] == "vector"


@pytest.mark.asyncio
async def test_vector_index_is_best_effort(monkeypatch, client):
    async def fake_summary(**kwargs):
        return True

    async def fake_fulltext(**kwargs):
        return False

    monkeypatch.setattr("src.api.routes.memory_retrieval.add_chapter_summary", fake_summary)
    monkeypatch.setattr("src.api.routes.memory_retrieval.add_chapter_fulltext", fake_fulltext)

    response = await client.post(
        "/internal/ai/stories/story-1/memory/index",
        json={
            "chapterNumber": 2,
            "title": "Mirror Oath",
            "summary": "Lin Jin swore the mirror oath.",
            "content": "Full chapter text.",
        },
    )

    assert response.status_code == 200
    assert response.json()["summaryIndexed"] is True
    assert response.json()["fulltextIndexed"] is False
    assert response.json()["vectorAvailable"] is True
