"""Internal draft quality-gate APIs for Java service."""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.services.consistency_service import ConsistencyCheckError, check_consistency
from src.services.review_service import ReviewGenerationError, review_quality

INPUT_ERROR_CODES = {
    "INVALID_CONSISTENCY_REQUEST",
    "INVALID_REVIEW_REQUEST",
    "GENERATION_ID_REQUIRED",
    "STORY_REQUIRED",
    "CHAPTER_REQUIRED",
    "BLUEPRINT_REQUIRED",
    "CONFIRMED_BLUEPRINT_REQUIRED",
    "CONFIRMED_OUTLINE_REQUIRED",
    "CONFIRMED_FINAL_OUTLINE_REQUIRED",
    "DRAFT_REQUIRED",
    "INVALID_RECENT_CHAPTERS",
}

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/chapters/{chapter_id}/drafts",
    tags=["internal-draft-gates"],
)


@router.post("/consistency")
async def check_draft_consistency(
    story_id: str,
    chapter_id: str,
    request: dict[str, Any],
):
    """Check a generated draft against confirmed writing context."""
    try:
        result = await check_consistency(request)
        return result.model_dump(by_alias=True)
    except ConsistencyCheckError as exc:
        raise HTTPException(
            status_code=400 if exc.code in INPUT_ERROR_CODES else 502,
            detail={
                "code": exc.code,
                "message": exc.message,
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        ) from exc


@router.post("/review")
async def review_draft_quality(
    story_id: str,
    chapter_id: str,
    request: dict[str, Any],
):
    """Review a generated draft against confirmed writing context."""
    try:
        result = await review_quality(request)
        return result.model_dump(by_alias=True)
    except ReviewGenerationError as exc:
        raise HTTPException(
            status_code=400 if exc.code in INPUT_ERROR_CODES else 502,
            detail={
                "code": exc.code,
                "message": exc.message,
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        ) from exc
