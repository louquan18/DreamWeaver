"""Internal blueprint generation API for Java service."""

from fastapi import APIRouter, HTTPException

from src.schemas.blueprint import LightBlueprintGenerateRequest, NovelBlueprintDraft
from src.services.blueprint_service import BlueprintGenerationError, generate_light_blueprint
from src.services.blueprint_validation import BlueprintValidationError

router = APIRouter(
    prefix="/internal/ai/stories/{story_id}/blueprints",
    tags=["internal-blueprints"],
)


@router.post("/generate", response_model=NovelBlueprintDraft)
async def generate_blueprint(
    story_id: str,
    request: LightBlueprintGenerateRequest,
) -> NovelBlueprintDraft:
    """Generate a lightweight NovelBlueprint draft for a story."""
    try:
        return await generate_light_blueprint(story_id, request)
    except BlueprintValidationError as exc:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "VALIDATION_ERROR",
                "message": str(exc),
                "storyId": story_id,
                "issues": [issue.model_dump() for issue in exc.errors],
            },
        ) from exc
    except BlueprintGenerationError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "AI_WORKER_ERROR",
                "message": str(exc),
                "storyId": story_id,
            },
        ) from exc
