"""Internal draft streaming API for Java service."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict, Field

from src.services.draft_service import stream_confirmed_outline_draft

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/chapters/{chapter_id}/drafts",
    tags=["internal-drafts"],
)


class DraftStreamRequest(BaseModel):
    """Java-owned writing context for confirmed-outline draft generation."""

    model_config = ConfigDict(populate_by_name=True)

    generation_id: str = Field(..., alias="generationId")
    user_id: str | None = Field(default=None, alias="userId")
    story: dict[str, Any] = Field(default_factory=dict)
    chapter: dict[str, Any] = Field(default_factory=dict)
    blueprint: dict[str, Any] = Field(default_factory=dict)
    confirmed_outline: dict[str, Any] = Field(default_factory=dict, alias="confirmedOutline")
    recent_chapters: list[dict[str, Any]] = Field(default_factory=list, alias="recentChapters")
    extra_prompt: str | None = Field(default=None, alias="extraPrompt")
    target_words: int | None = Field(default=None, alias="targetWords")
    model_profile: str | None = Field(default=None, alias="modelProfile")


@router.post("/stream")
async def stream_draft_from_confirmed_outline(
    story_id: str,
    chapter_id: str,
    request: DraftStreamRequest,
):
    """Stream a chapter draft using Java-supplied confirmed blueprint and outline."""
    if not request.confirmed_outline:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFIRMED_OUTLINE_REQUIRED",
                "message": "confirmedOutline is required for draft generation",
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        )
    if not request.blueprint:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "CONFIRMED_BLUEPRINT_REQUIRED",
                "message": "blueprint is required for draft generation",
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        )

    async def event_stream():
        draft_parts: list[str] = []
        yield _sse("node_start", {"node": "generate_draft", "progress": 50})
        try:
            payload = request.model_dump(by_alias=True)
            async for token in stream_confirmed_outline_draft(payload):
                draft_parts.append(token)
                yield _sse("token", {"content": token})
        except Exception as exc:  # noqa: BLE001 - convert model/transport failures to SSE error
            yield _sse("error", {"message": str(exc)})
            return

        draft = "".join(draft_parts)
        yield _sse("node_end", {"node": "generate_draft", "progress": 50})
        yield _sse(
            "done",
            {
                "story_id": story_id,
                "chapter_id": chapter_id,
                "generation_id": request.generation_id,
                "draft": draft,
                "word_count": len(draft),
                "tokens_streamed": len(draft_parts),
            },
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
