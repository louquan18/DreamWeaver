"""Schemas for pending memory changes extracted from confirmed drafts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MemoryChangeType = Literal["timeline", "character", "world", "foreshadow"]
MemoryChangeOperation = Literal["add", "update", "resolve", "deprecate"]
MemoryExtractionStatus = Literal["extracted", "partial", "blocked"]
MemoryWarningCode = Literal[
    "low_confidence",
    "conflict",
    "insufficient_evidence",
    "ambiguous_identity",
    "duplicate_candidate",
]


class MemorySourceSpan(BaseModel):
    """Where a pending memory change was evidenced in the confirmed draft."""

    model_config = ConfigDict(populate_by_name=True)

    start_offset: int | None = Field(default=None, alias="startOffset", ge=0)
    end_offset: int | None = Field(default=None, alias="endOffset", ge=0)
    quote: str = Field(..., min_length=1, max_length=280)

    @field_validator("quote")
    @classmethod
    def quote_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("sourceSpan.quote must not be blank")
        return stripped

    @model_validator(mode="after")
    def offsets_must_be_ordered(self) -> "MemorySourceSpan":
        if self.start_offset is not None and self.end_offset is not None:
            if self.end_offset <= self.start_offset:
                raise ValueError("sourceSpan.endOffset must be greater than startOffset")
        return self


class MemoryEvidence(BaseModel):
    """Short evidence that keeps extraction grounded in the confirmed draft."""

    model_config = ConfigDict(populate_by_name=True)

    quote: str = Field(..., min_length=1, max_length=280)
    source_span: MemorySourceSpan = Field(..., alias="sourceSpan")

    @field_validator("quote")
    @classmethod
    def quote_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("evidence.quote must not be blank")
        return stripped


class MemoryConflictHint(BaseModel):
    """A possible conflict against existing committed memory or locked facts."""

    model_config = ConfigDict(populate_by_name=True)

    target: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    severity: Literal["warning", "blocking"] = "warning"

    @field_validator("target", "message")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("conflict hint text must not be blank")
        return stripped


class BaseMemoryChange(BaseModel):
    """Common fields shared by all pending memory change types."""

    model_config = ConfigDict(populate_by_name=True)

    change_id: str = Field(..., alias="changeId", min_length=1)
    memory_type: MemoryChangeType = Field(..., alias="memoryType")
    operation: MemoryChangeOperation
    confidence: float = Field(..., ge=0, le=1)
    evidence: MemoryEvidence
    reasoning: str = Field(..., min_length=1)
    notes: str | None = None
    blocking: bool = False
    conflict: bool = False
    blocking_hints: list[str] = Field(default_factory=list, alias="blockingHints")
    conflict_hints: list[MemoryConflictHint] = Field(default_factory=list, alias="conflictHints")

    @field_validator("change_id", "reasoning", "notes")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("memory change text fields must not be blank")
        return stripped

    @field_validator("blocking_hints")
    @classmethod
    def hints_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("blockingHints must not contain blank items")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def conflict_flags_follow_hints(self) -> "BaseMemoryChange":
        if self.conflict_hints:
            self.conflict = True
        if self.blocking_hints or any(hint.severity == "blocking" for hint in self.conflict_hints):
            self.blocking = True
        return self


class TimelineMemoryChange(BaseMemoryChange):
    """A durable event or sequence change for the story timeline."""

    memory_type: Literal["timeline"] = Field("timeline", alias="memoryType")
    event: str = Field(..., min_length=1)
    order: int = Field(..., ge=0)
    timing: str = Field(..., min_length=1)
    participants: list[str] = Field(..., min_length=1)
    consequence: str = Field(..., min_length=1)

    @field_validator("event", "timing", "consequence")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("timeline fields must not be blank")
        return stripped

    @field_validator("participants")
    @classmethod
    def participants_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("timeline participants must not be blank")
        return [item.strip() for item in value]


class MemoryCharacterRef(BaseModel):
    """Character identity referenced by a pending memory change."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1)
    memory_id: str | None = Field(default=None, alias="memoryId")
    aliases: list[str] = Field(default_factory=list)

    @field_validator("name", "memory_id")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("character reference text must not be blank")
        return stripped

    @field_validator("aliases")
    @classmethod
    def aliases_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("character aliases must not be blank")
        return [item.strip() for item in value]


class CharacterMemoryChange(BaseMemoryChange):
    """A state, motivation, relationship, knowledge, or ability change."""

    memory_type: Literal["character"] = Field("character", alias="memoryType")
    character: MemoryCharacterRef
    change_kind: Literal[
        "identity",
        "state",
        "motivation",
        "relationship",
        "knowledge",
        "ability",
    ] = Field(
        ...,
        alias="changeKind",
    )
    before: str | None = None
    after: str = Field(..., min_length=1)
    related_characters: list[MemoryCharacterRef] = Field(
        default_factory=list,
        alias="relatedCharacters",
    )
    impact: str = Field(..., min_length=1)

    @field_validator("before", "after", "impact")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("character change text fields must not be blank")
        return stripped


class WorldMemoryChange(BaseMemoryChange):
    """A durable world rule, place, artifact, faction, or system change."""

    memory_type: Literal["world"] = Field("world", alias="memoryType")
    subject_type: Literal["rule", "location", "artifact", "faction", "system"] = Field(
        ...,
        alias="subjectType",
    )
    subject: str = Field(..., min_length=1)
    description: str = Field(..., min_length=1)
    scope: Literal["local", "story", "global"] = "story"
    impact: str = Field(..., min_length=1)

    @field_validator("subject", "description", "impact")
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("world change text fields must not be blank")
        return stripped


class ForeshadowMemoryChange(BaseMemoryChange):
    """A foreshadow lifecycle update extracted from the confirmed draft."""

    memory_type: Literal["foreshadow"] = Field("foreshadow", alias="memoryType")
    foreshadow_id: str | None = Field(default=None, alias="foreshadowId")
    lifecycle: Literal["planned", "planted", "strengthened", "triggered", "resolved", "abandoned"]
    content: str = Field(..., min_length=1)
    related_characters: list[str] = Field(default_factory=list, alias="relatedCharacters")
    related_items: list[str] = Field(default_factory=list, alias="relatedItems")
    related_locations: list[str] = Field(default_factory=list, alias="relatedLocations")
    payoff_hint: str | None = Field(default=None, alias="payoffHint")

    @field_validator("foreshadow_id", "content", "payoff_hint")
    @classmethod
    def optional_text_must_not_be_blank(cls, value: str | None) -> str | None:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("foreshadow text fields must not be blank")
        return stripped

    @field_validator("related_characters", "related_items", "related_locations")
    @classmethod
    def related_lists_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("foreshadow related lists must not contain blank items")
        return [item.strip() for item in value]

    @model_validator(mode="after")
    def existing_foreshadow_operations_need_id(self) -> "ForeshadowMemoryChange":
        if self.operation in {"update", "resolve", "deprecate"} and not self.foreshadow_id:
            raise ValueError("foreshadowId is required when updating, resolving, or deprecating")
        if (
            self.lifecycle in {"resolved", "abandoned"}
            and self.operation not in {"resolve", "deprecate"}
        ):
            raise ValueError(
                "resolved or abandoned foreshadow lifecycle requires resolve/deprecate operation"
            )
        return self


MemoryChange = (
    TimelineMemoryChange
    | CharacterMemoryChange
    | WorldMemoryChange
    | ForeshadowMemoryChange
)


class MemoryExtractionWarning(BaseModel):
    """A warning that must be shown before pending memories are confirmed."""

    model_config = ConfigDict(populate_by_name=True)

    code: MemoryWarningCode
    message: str = Field(..., min_length=1)
    change_ids: list[str] = Field(default_factory=list, alias="changeIds")

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("memory extraction warning message must not be blank")
        return stripped

    @field_validator("change_ids")
    @classmethod
    def change_ids_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("warning changeIds must not contain blank items")
        return [item.strip() for item in value]


class MemoryExtractionResult(BaseModel):
    """Structured pending memory changes extracted from a confirmed draft."""

    model_config = ConfigDict(populate_by_name=True)

    story_id: str = Field(..., alias="storyId", min_length=1)
    chapter_id: str = Field(..., alias="chapterId", min_length=1)
    source_generation_id: str = Field(..., alias="sourceGenerationId", min_length=1)
    schema_version: int = Field(default=1, alias="schemaVersion", ge=1)
    extractor_version: str = Field(
        default="memory-extractor-v1",
        alias="extractorVersion",
        min_length=1,
    )
    status: MemoryExtractionStatus
    summary: str = Field(..., min_length=1)
    changes: list[MemoryChange] = Field(default_factory=list)
    warnings: list[MemoryExtractionWarning] = Field(default_factory=list)

    @field_validator(
        "story_id",
        "chapter_id",
        "source_generation_id",
        "extractor_version",
        "summary",
    )
    @classmethod
    def text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("memory extraction result text fields must not be blank")
        return stripped

    @model_validator(mode="after")
    def change_ids_must_be_unique_and_warning_refs_known(self) -> "MemoryExtractionResult":
        change_ids = [change.change_id for change in self.changes]
        if len(change_ids) != len(set(change_ids)):
            raise ValueError("memory change changeId values must be unique")

        known_ids = set(change_ids)
        for warning in self.warnings:
            unknown = [change_id for change_id in warning.change_ids if change_id not in known_ids]
            if unknown:
                raise ValueError(
                    f"memory warning references unknown changeIds: {', '.join(unknown)}"
                )
        if self.status == "blocked" and not self.warnings:
            raise ValueError("blocked memory extraction must include warnings")
        return self


MEMORY_EXTRACTION_RESULT_JSON_SCHEMA = MemoryExtractionResult.model_json_schema(by_alias=True)
memory_extraction_result_json_schema = MEMORY_EXTRACTION_RESULT_JSON_SCHEMA
