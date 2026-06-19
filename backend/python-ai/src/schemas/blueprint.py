"""Schemas for lightweight novel blueprint generation."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class LightBlueprintGenerateRequest(BaseModel):
    """Request from Java service to generate a lightweight NovelBlueprint."""

    model_config = ConfigDict(populate_by_name=True)

    source_prompt: str = Field(..., alias="sourcePrompt", min_length=1, max_length=10000)
    genre: str | None = Field(default=None, max_length=80)
    tone: str | None = Field(default=None, max_length=120)
    target_words: int | None = Field(default=None, alias="targetWords", gt=0)
    preferences: dict[str, Any] = Field(default_factory=dict)

    @field_validator("source_prompt")
    @classmethod
    def source_prompt_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("sourcePrompt must not be blank")
        return stripped


class BlueprintValidationIssue(BaseModel):
    """Stable validation issue shape for blueprint errors and warnings."""

    code: str
    path: str
    message: str
    severity: Literal["error", "warning"]
    blocking: bool


class NovelBlueprintDraft(BaseModel):
    """Structured generated blueprint aligned with the P1 NovelBlueprint model."""

    model_config = ConfigDict(populate_by_name=True)

    story_id: str = Field(..., alias="storyId")
    source_prompt: str = Field(..., alias="sourcePrompt")
    premise: str
    genre: str | None = None
    tone: str | None = None
    protagonist: dict[str, Any]
    main_thread: dict[str, Any] = Field(..., alias="mainThread")
    core_conflict: dict[str, Any] = Field(..., alias="coreConflict")
    world_seed: dict[str, Any] = Field(..., alias="worldSeed")
    writing_preferences: dict[str, Any] = Field(..., alias="writingPreferences")
    locked_facts: list[dict[str, Any]] = Field(..., alias="lockedFacts")
    validation_issues: list[BlueprintValidationIssue] = Field(
        default_factory=list,
        alias="validationIssues",
    )
    status: str = "generated"

    @field_validator("premise")
    @classmethod
    def premise_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("premise must not be blank")
        return stripped

    @field_validator(
        "protagonist",
        "main_thread",
        "core_conflict",
        "world_seed",
        "writing_preferences",
    )
    @classmethod
    def object_fields_must_be_dict(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("blueprint object fields must be JSON objects")
        return value

    @field_validator("locked_facts")
    @classmethod
    def locked_facts_must_have_text(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in value:
            if not isinstance(item, dict) or not str(item.get("text", "")).strip():
                raise ValueError("each locked fact must be an object with non-empty text")
        return value
