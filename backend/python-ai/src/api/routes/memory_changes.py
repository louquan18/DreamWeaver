"""Internal memory-change extraction API for Java service."""

from typing import Any

from fastapi import APIRouter, HTTPException

from src.services import memory_conflict_service, memory_extraction_service
from src.services.memory_conflict_service import MemoryConflictDetectionError
from src.services.memory_extraction_service import MemoryExtractionGenerationError

INPUT_ERROR_CODES = {
    "INVALID_MEMORY_EXTRACTION_REQUEST",
    "STORY_ID_REQUIRED",
    "CHAPTER_ID_REQUIRED",
    "SOURCE_GENERATION_ID_REQUIRED",
    "CONFIRMED_DRAFT_REQUIRED",
    "INVALID_STORY",
    "INVALID_CHAPTER",
    "INVALID_BLUEPRINT",
    "INVALID_CONFIRMED_OUTLINE",
    "INVALID_EXISTING_MEMORY",
    "INVALID_METADATA",
    "INVALID_GENERATION_METADATA",
    "INVALID_REVIEW_METADATA",
    "INVALID_CONSISTENCY_METADATA",
    "INVALID_REPAIR_METADATA",
    "INVALID_RECENT_CHAPTERS",
    "PATH_BODY_STORY_ID_MISMATCH",
    "PATH_BODY_CHAPTER_ID_MISMATCH",
}

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/chapters/{chapter_id}/memory-changes",
    tags=["internal-memory-changes"],
)


@router.post("/extract")
async def extract_memory_changes_from_confirmed_draft(
    story_id: str,
    chapter_id: str,
    request: dict[str, Any],
):
    """Extract pending memory changes and annotate deterministic conflict hints."""
    try:
        _assert_path_matches_body(story_id, chapter_id, request)
        result = await memory_extraction_service.extract_memory_from_confirmed_draft(request)
        checked = memory_conflict_service.detect_memory_conflicts(result, request)
        return checked.model_dump(by_alias=True)
    except MemoryExtractionGenerationError as exc:
        raise HTTPException(
            status_code=400 if exc.code in INPUT_ERROR_CODES else 502,
            detail={
                "code": exc.code,
                "message": exc.message,
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        ) from exc
    except MemoryConflictDetectionError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": exc.code,
                "message": exc.message,
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        ) from exc


def _assert_path_matches_body(story_id: str, chapter_id: str, request: dict[str, Any]) -> None:
    if str(request.get("storyId") or "").strip() != story_id:
        raise MemoryExtractionGenerationError(
            "PATH_BODY_STORY_ID_MISMATCH",
            "storyId in request body must match path story_id",
        )
    if str(request.get("chapterId") or "").strip() != chapter_id:
        raise MemoryExtractionGenerationError(
            "PATH_BODY_CHAPTER_ID_MISMATCH",
            "chapterId in request body must match path chapter_id",
        )
