"""Schemas for P0 draft auto-repair tasks."""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.schemas.consistency import DraftConsistencyReport
from src.schemas.review import DraftQualityReviewReport

RepairStrategy = Literal["local", "full_chapter"]


class DraftRepairRequest(BaseModel):
    """Java-owned context and review gates required by P0 auto repair."""

    model_config = ConfigDict(populate_by_name=True)

    generation_id: str = Field(..., alias="generationId", min_length=1)
    story: dict[str, Any]
    chapter: dict[str, Any]
    blueprint: dict[str, Any]
    confirmed_outline: dict[str, Any] = Field(..., alias="confirmedOutline")
    draft: str = Field(..., min_length=1)
    review_report: DraftQualityReviewReport = Field(..., alias="reviewReport")
    consistency_report: DraftConsistencyReport = Field(..., alias="consistencyReport")
    recent_chapters: list[dict[str, Any]] = Field(default_factory=list, alias="recentChapters")
    extra_prompt: str | None = Field(default=None, alias="extraPrompt")
    max_repair_rounds: int = Field(default=1, alias="maxRepairRounds", ge=1, le=3)

    @field_validator("generation_id", "draft")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("repair request text fields must not be blank")
        return stripped

    @field_validator("story", "chapter", "blueprint", "confirmed_outline")
    @classmethod
    def required_objects_must_not_be_empty(cls, value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict) or not value:
            raise ValueError("repair context objects must be non-empty JSON objects")
        return value

    @field_validator("recent_chapters")
    @classmethod
    def recent_chapters_must_be_objects(cls, value: list[dict[str, Any]]) -> list[dict[str, Any]]:
        for item in value:
            if not isinstance(item, dict):
                raise ValueError("recentChapters items must be JSON objects")
        return value

    @field_validator("extra_prompt")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None

    @model_validator(mode="after")
    def confirmed_outline_must_have_final_outline(self) -> "DraftRepairRequest":
        final_outline = self.confirmed_outline.get("finalOutline")
        if not isinstance(final_outline, dict) or not final_outline:
            raise ValueError("confirmedOutline.finalOutline is required")
        return self


class DraftRepairResult(BaseModel):
    """Structured result returned by the P0 auto-repair task."""

    model_config = ConfigDict(populate_by_name=True)

    generation_id: str = Field(..., alias="generationId", min_length=1)
    repaired_draft: str = Field(..., alias="repairedDraft", min_length=1)
    repair_summary: str = Field(..., alias="repairSummary", min_length=1)
    repaired_issue_ids: list[str] = Field(default_factory=list, alias="repairedIssueIds")
    remaining_issue_ids: list[str] = Field(default_factory=list, alias="remainingIssueIds")
    strategy: RepairStrategy
    changed: bool

    @field_validator("generation_id", "repaired_draft", "repair_summary")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("repair result text fields must not be blank")
        return stripped

    @field_validator("repaired_issue_ids", "remaining_issue_ids")
    @classmethod
    def issue_ids_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("repair issue id lists must not contain blank items")
        return [item.strip() for item in value]


DRAFT_REPAIR_REQUEST_JSON_SCHEMA = DraftRepairRequest.model_json_schema()
DRAFT_REPAIR_RESULT_JSON_SCHEMA = DraftRepairResult.model_json_schema()

draft_repair_request_json_schema = DRAFT_REPAIR_REQUEST_JSON_SCHEMA
draft_repair_result_json_schema = DRAFT_REPAIR_RESULT_JSON_SCHEMA
