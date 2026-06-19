"""Schemas for chapter outline options and confirmed outlines."""

from typing import Literal

from pydantic import AliasChoices, BaseModel, ConfigDict, Field, field_validator

OutlineOptionCode = Literal["A", "B", "C"]
OutlineOptionType = Literal["steady", "conflict", "foreshadow"]
ForeshadowActionType = Literal["plant", "strengthen", "trigger", "resolve"]
MemoryReferenceType = Literal["blueprint", "timeline", "character", "world", "foreshadow", "chapter"]


class OutlineScene(BaseModel):
    """One scene beat inside a 3-5 scene chapter outline."""

    model_config = ConfigDict(populate_by_name=True)

    order: int = Field(..., ge=1)
    summary: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    characters: list[str] = Field(default_factory=list)
    location: str | None = None
    pov_character: str | None = Field(default=None, alias="povCharacter")
    tension: str | None = None
    outcome: str = Field(..., min_length=1)

    @field_validator("summary", "purpose", "outcome")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("scene text fields must not be blank")
        return stripped


class OutlineCharacter(BaseModel):
    """Character participation and motivation for the chapter."""

    model_config = ConfigDict(populate_by_name=True)

    name: str = Field(..., min_length=1)
    role: str | None = None
    motivation: str = Field(..., min_length=1)
    state_change: str | None = Field(default=None, alias="stateChange")

    @field_validator("name", "motivation")
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("character name and motivation must not be blank")
        return stripped


class OutlineConflict(BaseModel):
    """Main external/internal conflict and stakes for the chapter."""

    model_config = ConfigDict(populate_by_name=True)

    external: str | None = None
    internal: str | None = None
    stakes: str = Field(..., min_length=1)

    @field_validator("stakes")
    @classmethod
    def stakes_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("conflict.stakes must not be blank")
        return stripped


class ForeshadowAction(BaseModel):
    """Foreshadow planting, strengthening, triggering, or resolving action."""

    model_config = ConfigDict(populate_by_name=True)

    action: ForeshadowActionType
    description: str = Field(..., min_length=1)
    foreshadow_id: str | None = Field(default=None, alias="foreshadowId")
    evidence: str | None = None
    payoff_hint: str | None = Field(default=None, alias="payoffHint")

    @field_validator("description")
    @classmethod
    def description_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("foreshadow action description must not be blank")
        return stripped


class MemoryReference(BaseModel):
    """History or memory item used to justify the outline."""

    model_config = ConfigDict(populate_by_name=True)

    type: MemoryReferenceType = Field(
        ...,
        validation_alias=AliasChoices("type", "memoryType"),
        serialization_alias="memoryType",
    )
    summary: str = Field(..., min_length=1)
    memory_id: str | None = Field(
        default=None,
        validation_alias=AliasChoices("memoryId", "referenceId", "memory_id"),
        serialization_alias="memoryId",
    )
    relevance: str | None = None

    @field_validator("summary")
    @classmethod
    def summary_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("memory reference summary must not be blank")
        return stripped


class ChapterOutlineContent(BaseModel):
    """Standard JSON shape shared by outline options and final confirmed outlines."""

    model_config = ConfigDict(populate_by_name=True)

    title_candidates: list[str] = Field(..., alias="titleCandidates", min_length=1, max_length=5)
    chapter_goal: str = Field(..., alias="chapterGoal", min_length=1)
    story_summary: str = Field(..., alias="storySummary", min_length=1)
    scene_outline: list[OutlineScene] = Field(..., alias="sceneOutline", min_length=3, max_length=5)
    characters_involved: list[OutlineCharacter] = Field(..., alias="charactersInvolved", min_length=1)
    conflict: OutlineConflict
    highlight_moment: str = Field(..., alias="highlightMoment", min_length=1)
    foreshadow_actions: list[ForeshadowAction] = Field(default_factory=list, alias="foreshadowActions")
    memory_references: list[MemoryReference] = Field(default_factory=list, alias="memoryReferences")
    why_this_plan: str = Field(..., alias="whyThisPlan", min_length=1)
    ending_hook: str = Field(..., alias="endingHook", min_length=1)
    risk_notes: list[str] = Field(default_factory=list, alias="riskNotes")

    @field_validator(
        "chapter_goal",
        "story_summary",
        "highlight_moment",
        "why_this_plan",
        "ending_hook",
    )
    @classmethod
    def required_text_must_not_be_blank(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("outline text fields must not be blank")
        return stripped

    @field_validator("title_candidates", "risk_notes")
    @classmethod
    def list_text_must_not_be_blank(cls, value: list[str]) -> list[str]:
        for item in value:
            if not isinstance(item, str) or not item.strip():
                raise ValueError("outline list text items must not be blank")
        return [item.strip() for item in value]


class ChapterOutlineOptionDraft(ChapterOutlineContent):
    """Generated A/B/C chapter outline option returned by the AI worker."""

    model_config = ConfigDict(populate_by_name=True)

    story_id: str = Field(..., alias="storyId")
    chapter_id: str = Field(..., alias="chapterId")
    option_group_id: str | None = Field(default=None, alias="optionGroupId")
    option_code: OutlineOptionCode = Field(..., alias="optionCode")
    option_type: OutlineOptionType = Field(..., alias="optionType")
    status: Literal["generated"] = "generated"


class ChapterOutlineOptionsDraft(BaseModel):
    """A full A/B/C outline option set for one chapter."""

    model_config = ConfigDict(populate_by_name=True)

    story_id: str = Field(..., alias="storyId")
    chapter_id: str = Field(..., alias="chapterId")
    option_group_id: str | None = Field(default=None, alias="optionGroupId")
    options: list[ChapterOutlineOptionDraft] = Field(..., min_length=3, max_length=3)

    @field_validator("options")
    @classmethod
    def options_must_cover_a_b_c(cls, value: list[ChapterOutlineOptionDraft]):
        codes = {option.option_code for option in value}
        types = {option.option_type for option in value}
        if codes != {"A", "B", "C"}:
            raise ValueError("outline options must include exactly A, B, and C")
        if types != {"steady", "conflict", "foreshadow"}:
            raise ValueError("outline options must include steady, conflict, and foreshadow")
        return value


class ChapterOutlineDraft(BaseModel):
    """Author-selected and adjusted final chapter outline."""

    model_config = ConfigDict(populate_by_name=True)

    story_id: str = Field(..., alias="storyId")
    chapter_id: str = Field(..., alias="chapterId")
    source_option_ids: list[str] = Field(default_factory=list, alias="sourceOptionIds")
    user_feedback: str | None = Field(default=None, alias="userFeedback")
    final_outline: ChapterOutlineContent = Field(..., alias="finalOutline")
    status: Literal["draft", "confirmed"] = "draft"


CHAPTER_OUTLINE_CONTENT_JSON_SCHEMA = ChapterOutlineContent.model_json_schema()
CHAPTER_OUTLINE_OPTION_JSON_SCHEMA = ChapterOutlineOptionDraft.model_json_schema()
CHAPTER_OUTLINE_OPTIONS_JSON_SCHEMA = ChapterOutlineOptionsDraft.model_json_schema()

ConfirmedChapterOutlineDraft = ChapterOutlineDraft
chapter_outline_content_json_schema = CHAPTER_OUTLINE_CONTENT_JSON_SCHEMA
chapter_outline_option_json_schema = CHAPTER_OUTLINE_OPTION_JSON_SCHEMA
chapter_outline_options_json_schema = CHAPTER_OUTLINE_OPTIONS_JSON_SCHEMA
