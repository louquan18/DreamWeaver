"""Internal draft streaming API for Java service."""

import json
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.services.draft_service import (
    DraftGenerationInputError,
    stream_generate_draft,
    validate_generate_draft_request,
)

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/chapters/{chapter_id}/drafts",
    tags=["internal-drafts"],
)


@router.post("/stream")
async def stream_draft_from_confirmed_outline(
    story_id: str,
    chapter_id: str,
    request: dict[str, Any],
):
    """Stream a chapter draft using Java-supplied confirmed blueprint and outline."""
    try:
        draft_request = validate_generate_draft_request(request)
    except DraftGenerationInputError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": exc.code,
                "message": exc.message,
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        ) from exc

    async def event_stream():
        async for item in stream_generate_draft(
            draft_request,
            story_id=story_id,
            chapter_id=chapter_id,
        ):
            yield _sse(item.event, item.data)

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
