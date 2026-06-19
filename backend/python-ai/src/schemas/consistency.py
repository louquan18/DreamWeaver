"""Schemas for draft consistency rules and reports."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

ConsistencySeverity = Literal["P0", "P1", "P2"]
ConsistencyDomain = Literal["world", "character", "timeline", "foreshadow"]


class ConsistencyIssueLocation(BaseModel):
    """Optional location metadata for a consistency issue."""

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


class ConsistencyRule(BaseModel):
    """One structured consistency rule used by the consistency checker."""

    model_config = ConfigDict(populate_by_name=True)

    rule_id: str = Field(..., alias="ruleId", min_length=1)
    domain: ConsistencyDomain
    severity: ConsistencySeverity
    description: str = Field(..., min_length=1)
    required_context: list[str] = Field(..., alias="requiredContext", min_length=1)
    check_hint: str = Field(..., alias="checkHint", min_length=1)
    repair_hint: str = Field(..., alias="repairHint", min_length=1)
    blocking: bool = False
    auto_repair_required: bool = Field(default=False, alias="autoRepairRequired")

    @field_validator("rule_id", "description", "check_hint", "repair_hint")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("consistency rule text fields must not be blank")
        return stripped

    @field_validator("required_context")
    @classmethod
    def required_context_items_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("requiredContext items must not be blank")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def p0_rule_requires_repair_gate(self) -> "ConsistencyRule":
        if self.severity == "P0":
            self.blocking = True
            self.auto_repair_required = True
        return self


class ConsistencyIssue(BaseModel):
    """One consistency issue found in a generated draft."""

    model_config = ConfigDict(populate_by_name=True)

    severity: ConsistencySeverity
    domain: ConsistencyDomain
    rule_id: str = Field(..., alias="ruleId", min_length=1)
    message: str = Field(..., min_length=1)
    evidence: str = Field(..., min_length=1)
    suggestion: str = Field(..., min_length=1)
    location: ConsistencyIssueLocation | None = None
    scene_index: int | None = Field(default=None, alias="sceneIndex", ge=0)
    blocking: bool = False
    auto_repair_required: bool = Field(default=False, alias="autoRepairRequired")

    @field_validator("rule_id", "message", "evidence", "suggestion")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("consistency issue text fields must not be blank")
        return stripped

    @model_validator(mode="after")
    def p0_issue_requires_repair_gate(self) -> "ConsistencyIssue":
        if self.severity == "P0":
            self.blocking = True
            self.auto_repair_required = True
        return self


class DraftConsistencyReport(BaseModel):
    """Structured report produced by a future draft consistency checker."""

    model_config = ConfigDict(populate_by_name=True)

    summary: str = Field(..., min_length=1)
    issues: list[ConsistencyIssue] = Field(default_factory=list)
    checked_rule_ids: list[str] = Field(default_factory=list, alias="checkedRuleIds")
    passed_rule_ids: list[str] = Field(default_factory=list, alias="passedRuleIds")
    blocking: bool = False
    auto_repair_required: bool = Field(default=False, alias="autoRepairRequired")

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("consistency report summary must not be blank")
        return stripped

    @field_validator("checked_rule_ids", "passed_rule_ids")
    @classmethod
    def rule_ids_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("rule id lists must not contain blank items")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def p0_issues_gate_report(self) -> "DraftConsistencyReport":
        has_p0 = any(issue.severity == "P0" for issue in self.issues)
        if has_p0:
            self.blocking = True
            self.auto_repair_required = True
        return self


CONSISTENCY_RULE_JSON_SCHEMA = ConsistencyRule.model_json_schema()
DRAFT_CONSISTENCY_REPORT_JSON_SCHEMA = DraftConsistencyReport.model_json_schema()

consistency_rule_json_schema = CONSISTENCY_RULE_JSON_SCHEMA
draft_consistency_report_json_schema = DRAFT_CONSISTENCY_REPORT_JSON_SCHEMA
