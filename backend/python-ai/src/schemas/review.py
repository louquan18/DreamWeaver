"""Schemas for AI quality review reports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ReviewSeverity = Literal["P0", "P1", "P2"]
ReviewIssueCategory = Literal[
    "plot",
    "character",
    "world",
    "timeline",
    "foreshadow",
    "style",
    "pacing",
    "continuity",
]


class ReviewIssueLocation(BaseModel):
    """Optional location metadata for a draft issue."""

    model_config = ConfigDict(populate_by_name=True)

    chapter_id: str | None = Field(default=None, alias="chapterId")
    scene_index: int | None = Field(default=None, alias="sceneIndex", ge=0)
    paragraph_index: int | None = Field(default=None, alias="paragraphIndex", ge=0)
    start_offset: int | None = Field(default=None, alias="startOffset", ge=0)
    end_offset: int | None = Field(default=None, alias="endOffset", ge=0)
    quote: str | None = None

    @field_validator("quote")
    @classmethod
    def optional_quote_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is not None and not value.strip():
            raise ValueError("location.quote must not be blank")
        return value.strip() if value is not None else value


class ReviewIssue(BaseModel):
    """One quality issue found in a generated draft."""

    model_config = ConfigDict(populate_by_name=True)

    severity: ReviewSeverity
    category: ReviewIssueCategory
    message: str = Field(..., min_length=1)
    evidence: str = Field(..., min_length=1)
    suggestion: str = Field(..., min_length=1)
    location: ReviewIssueLocation | None = None
    scene_index: int | None = Field(default=None, alias="sceneIndex", ge=0)
    blocking: bool = False
    auto_repair_required: bool = Field(default=False, alias="autoRepairRequired")

    @field_validator("message", "evidence", "suggestion")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("review issue text fields must not be blank")
        return stripped

    @model_validator(mode="after")
    def p0_issue_requires_repair_gate(self) -> "ReviewIssue":
        if self.severity == "P0":
            self.blocking = True
            self.auto_repair_required = True
        return self


class DraftQualityReviewReport(BaseModel):
    """Structured P0/P1/P2 review report for draft quality gates."""

    model_config = ConfigDict(populate_by_name=True)

    overall_score: int = Field(..., alias="overallScore", ge=0, le=100)
    summary: str = Field(..., min_length=1)
    issues: list[ReviewIssue] = Field(default_factory=list)
    blocking: bool = False
    auto_repair_required: bool = Field(default=False, alias="autoRepairRequired")
    revision_hints: list[str] = Field(default_factory=list, alias="revisionHints")
    strengths: list[str] = Field(default_factory=list)

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("review summary must not be blank")
        return stripped

    @field_validator("revision_hints", "strengths")
    @classmethod
    def list_text_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("review list text items must not be blank")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def p0_issues_gate_report(self) -> "DraftQualityReviewReport":
        has_p0 = any(issue.severity == "P0" for issue in self.issues)
        if has_p0:
            self.blocking = True
            self.auto_repair_required = True
        return self


DRAFT_QUALITY_REVIEW_JSON_SCHEMA = DraftQualityReviewReport.model_json_schema()
draft_quality_review_json_schema = DRAFT_QUALITY_REVIEW_JSON_SCHEMA

