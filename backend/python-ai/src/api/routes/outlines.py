"""Internal chapter outline options generation API for Java service."""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from src.schemas.outline import ChapterOutlineOptionsDraft
from src.services.outline_service import OutlineGenerationError, generate_outline_options

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/chapters/{chapter_id}/outline-options",
    tags=["internal-outlines"],
)


class OutlineOptionsGenerateRequest(BaseModel):
    """Context payload supplied by the Java orchestration layer."""

    model_config = ConfigDict(populate_by_name=True)

    option_group_id: str | None = Field(default=None, alias="optionGroupId")
    story: dict[str, Any] | None = None
    chapter: dict[str, Any] | None = None
    blueprint: dict[str, Any] | None = None
    author_intent: dict[str, Any] | None = Field(default=None, alias="authorIntent")
    recent_chapters: list[dict[str, Any]] = Field(default_factory=list, alias="recentChapters")
    timeline: list[dict[str, Any]] = Field(default_factory=list)
    characters: list[dict[str, Any]] = Field(default_factory=list)
    world: list[dict[str, Any]] = Field(default_factory=list)
    foreshadows: list[dict[str, Any]] = Field(default_factory=list)
    additional_memory: list[dict[str, Any]] = Field(default_factory=list, alias="additionalMemory")


@router.post("/generate", response_model=ChapterOutlineOptionsDraft)
async def generate_chapter_outline_options(
    story_id: str,
    chapter_id: str,
    request: OutlineOptionsGenerateRequest,
) -> ChapterOutlineOptionsDraft:
    """Generate A/B/C chapter outline options for a story chapter."""
    if not str(request.option_group_id or "").strip():
        raise HTTPException(
            status_code=400,
            detail={
                "code": "OPTION_GROUP_ID_REQUIRED",
                "message": "optionGroupId is required for outline options generation",
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        )

    try:
        return await generate_outline_options(
            story_id=story_id,
            chapter_id=chapter_id,
            option_group_id=request.option_group_id,
            story=request.story,
            chapter=request.chapter,
            blueprint=request.blueprint,
            author_intent=request.author_intent,
            recent_chapters=request.recent_chapters,
            timeline=request.timeline,
            characters=request.characters,
            world=request.world,
            foreshadows=request.foreshadows,
            additional_memory=request.additional_memory,
        )
    except OutlineGenerationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "OUTLINE_GENERATION_ERROR",
                "message": str(exc),
                "storyId": story_id,
                "chapterId": chapter_id,
            },
        ) from exc
