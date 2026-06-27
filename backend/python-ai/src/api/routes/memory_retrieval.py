"""Internal vector-backed additional memory retrieval API."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.memory.vector_store import (
    add_chapter_fulltext,
    add_chapter_summary,
    search_relevant_chapters,
    search_relevant_paragraphs,
)

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/memory",
    tags=["internal-memory-retrieval"],
)


class MemoryIndexRequest(BaseModel):
    """Confirmed chapter text and summary to index into the vector store."""

    model_config = ConfigDict(populate_by_name=True)

    chapter_number: int = Field(..., alias="chapterNumber", ge=0)
    title: str | None = None
    summary: str | None = None
    content: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("title", "summary", "content")
    @classmethod
    def blank_text_to_none(cls, value: str | None) -> str | None:
        if value is None:
            return None
        text = value.strip()
        return text or None


class MemoryRetrieveRequest(BaseModel):
    """Vector retrieval query for additionalMemory."""

    model_config = ConfigDict(populate_by_name=True)

    query: str = Field(..., min_length=1)
    k: int = Field(default=8, ge=1, le=20)
    chapter_range: list[int] | None = Field(default=None, alias="chapterRange")

    @field_validator("query")
    @classmethod
    def query_must_not_be_blank(cls, value: str) -> str:
        text = value.strip()
        if not text:
            raise ValueError("query must not be blank")
        return text

    @field_validator("chapter_range")
    @classmethod
    def chapter_range_must_have_two_values(cls, value: list[int] | None) -> list[int] | None:
        if value is not None and len(value) != 2:
            raise ValueError("chapterRange must contain [start, end]")
        return value


@router.post("/index")
async def index_chapter_memory(
    story_id: str,
    request: MemoryIndexRequest,
) -> dict[str, Any]:
    """Best-effort Chroma indexing for confirmed chapter summary and fulltext chunks."""
    summary_indexed = False
    fulltext_indexed = False

    if request.summary:
        summary_indexed = await add_chapter_summary(
            story_id=story_id,
            chapter_number=request.chapter_number,
            summary=request.summary,
            metadata={
                "title": request.title,
                **request.metadata,
            },
        )

    if request.content:
        fulltext_indexed = await add_chapter_fulltext(
            story_id=story_id,
            chapter_number=request.chapter_number,
            content=request.content,
        )

    return {
        "storyId": story_id,
        "chapterNumber": request.chapter_number,
        "summaryIndexed": summary_indexed,
        "fulltextIndexed": fulltext_indexed,
        "vectorAvailable": summary_indexed or fulltext_indexed,
    }


@router.post("/retrieve")
async def retrieve_additional_memory(
    story_id: str,
    request: MemoryRetrieveRequest,
) -> dict[str, Any]:
    """Return bounded vector hits normalized to the additionalMemory contract."""
    if request.chapter_range is not None and request.chapter_range[0] > request.chapter_range[1]:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "INVALID_CHAPTER_RANGE",
                "message": "chapterRange start must be <= end",
                "storyId": story_id,
            },
        )

    chapter_range = tuple(request.chapter_range) if request.chapter_range else None
    paragraphs = await search_relevant_paragraphs(
        story_id=story_id,
        query=request.query,
        k=request.k,
        chapter_range=chapter_range,
    )
    summaries = await search_relevant_chapters(
        story_id=story_id,
        query=request.query,
        k=request.k,
    )

    additional_memory = _normalize_hits(paragraphs, summaries, request.k)
    return {
        "storyId": story_id,
        "retrievalMethod": "vector" if additional_memory else "none",
        "additionalMemory": additional_memory,
    }


def _normalize_hits(
    paragraphs: list[dict[str, Any]],
    summaries: list[dict[str, Any]],
    limit: int,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for hit in paragraphs:
        chapter_number = int(hit.get("chapter_number") or 0)
        paragraph_index = int(hit.get("paragraph_index") or 0)
        identity = f"paragraph:{chapter_number}:{paragraph_index}"
        if identity in seen:
            continue
        seen.add(identity)
        items.append({
            "id": f"am-vector-{identity.replace(':', '-')}",
            "type": "paragraph",
            "content": str(hit.get("text") or ""),
            "chapterNumber": chapter_number,
            "reason": "vector paragraph match",
            "source": {
                "chapterNumber": chapter_number,
                "paragraphIndex": paragraph_index,
            },
            "score": _score(hit.get("distance")),
            "retrievalMethod": "vector",
        })

    for hit in summaries:
        chapter_number = int(hit.get("chapter_number") or 0)
        identity = f"chapter_summary:{chapter_number}"
        if identity in seen:
            continue
        seen.add(identity)
        items.append({
            "id": f"am-vector-summary-{chapter_number}",
            "type": "chapter_summary",
            "content": str(hit.get("summary") or ""),
            "chapterNumber": chapter_number,
            "reason": "vector chapter summary match",
            "source": {
                "chapterNumber": chapter_number,
            },
            "score": _score(hit.get("distance")),
            "retrievalMethod": "vector",
        })

    return [item for item in items if item["content"]][:limit]


def _score(distance: Any) -> float:
    try:
        return max(0.0, min(1.0, 1.0 - float(distance)))
    except Exception:
        return 0.0
