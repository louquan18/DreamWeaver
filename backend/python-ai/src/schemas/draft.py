"""Schemas for confirmed-outline draft generation tasks."""

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

DEFAULT_DRAFT_TARGET_WORDS = 2000


class DraftGenerateRequest(BaseModel):
    """Java-owned context required by the generate_draft task."""

    model_config = ConfigDict(populate_by_name=True)

    generation_id: str = Field(..., alias="generationId", min_length=1)
    user_id: str | None = Field(default=None, alias="userId")
    story: dict[str, Any]
    chapter: dict[str, Any]
    blueprint: dict[str, Any]
    confirmed_outline: dict[str, Any] = Field(..., alias="confirmedOutline")
    recent_chapters: list[dict[str, Any]] = Field(default_factory=list, alias="recentChapters")
    extra_prompt: str | None = Field(default=None, alias="extraPrompt")
    target_words: int = Field(default=DEFAULT_DRAFT_TARGET_WORDS, alias="targetWords", gt=0)
    model_profile: str | None = Field(default=None, alias="modelProfile")

    @field_validator("generation_id")
    @classmethod
    def generation_id_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("generationId must not be blank")
        return stripped

    @field_validator("user_id", "extra_prompt", "model_profile")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @field_validator("story", "chapter", "blueprint", "confirmed_outline")
    @classmethod
    def required_objects_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or not value:
            raise ValueError("draft context objects must be non-empty JSON objects")
        return value

    @field_validator("recent_chapters")
    @classmethod
    def recent_chapters_must_be_objects(
        cls,
        value: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("recentChapters items must be JSON objects")
        return value

    @field_validator("target_words", mode="before")
    @classmethod
    def empty_target_words_use_default(cls, value: Any) -> Any:
        if value is None or value == "":
            return DEFAULT_DRAFT_TARGET_WORDS
        return value

    @model_validator(mode="after")
    def confirmed_outline_must_have_final_outline(self) -> "DraftGenerateRequest":
        final_outline = self.confirmed_outline.get("finalOutline")
        if not isinstance(final_outline, dict) or not final_outline:
            raise ValueError("confirmedOutline.finalOutline is required")
        return self

    def writer_payload(self) -> dict[str, Any]:
        """Return the camelCase payload used by Writer prompt construction."""
        return self.model_dump(by_alias=True)


class DraftGenerateResult(BaseModel):
    """Stable generate_draft completion payload emitted through SSE done."""

    story_id: str = Field(..., alias="story_id", min_length=1)
    chapter_id: str = Field(..., alias="chapter_id", min_length=1)
    generation_id: str = Field(..., alias="generation_id", min_length=1)
    draft: str
    word_count: int = Field(..., alias="word_count", ge=0)
    tokens_streamed: int = Field(..., alias="tokens_streamed", ge=0)

    @field_validator("story_id", "chapter_id", "generation_id")
    @classmethod
    def ids_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("draft result ids must not be blank")
        return stripped

    def sse_payload(self) -> dict[str, Any]:
        """Return the Java-compatible snake_case done payload."""
        return self.model_dump(by_alias=True)


DRAFT_GENERATE_REQUEST_JSON_SCHEMA = DraftGenerateRequest.model_json_schema()
DRAFT_GENERATE_RESULT_JSON_SCHEMA = DraftGenerateResult.model_json_schema()

draft_generate_request_json_schema = DRAFT_GENERATE_REQUEST_JSON_SCHEMA
draft_generate_result_json_schema = DRAFT_GENERATE_RESULT_JSON_SCHEMA
