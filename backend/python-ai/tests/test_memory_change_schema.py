import pytest
from pydantic import ValidationError

from src.schemas.memory import (
    MEMORY_EXTRACTION_RESULT_JSON_SCHEMA,
    CharacterMemoryChange,
    ForeshadowMemoryChange,
    MemoryExtractionResult,
    TimelineMemoryChange,
    WorldMemoryChange,
)


def test_memory_extraction_result_accepts_four_memory_change_types():
    result = MemoryExtractionResult.model_validate(
        {
            "storyId": "story-1",
            "chapterId": "chapter-3",
            "sourceGenerationId": "generation-1",
            "status": "extracted",
            "summary": "Four pending memories were extracted.",
            "changes": [
                timeline_change(),
                character_change(),
                world_change(),
                foreshadow_change(),
            ],
        }
    )

    assert isinstance(result.changes[0], TimelineMemoryChange)
    assert isinstance(result.changes[1], CharacterMemoryChange)
    assert isinstance(result.changes[2], WorldMemoryChange)
    assert isinstance(result.changes[3], ForeshadowMemoryChange)


def test_memory_extraction_result_serializes_with_camel_case_contract():
    result = MemoryExtractionResult.model_validate(
        {
            "storyId": "story-1",
            "chapterId": "chapter-3",
            "sourceGenerationId": "generation-1",
            "status": "partial",
            "summary": "One change needs review.",
            "changes": [timeline_change()],
            "warnings": [
                {
                    "code": "low_confidence",
                    "message": "The timeline consequence is implied and should be reviewed.",
                    "changeIds": ["memchg-timeline-1"],
                }
            ],
        }
    )

    dumped = result.model_dump(by_alias=True)

    assert dumped["sourceGenerationId"] == "generation-1"
    assert dumped["schemaVersion"] == 1
    assert dumped["changes"][0]["changeId"] == "memchg-timeline-1"
    assert dumped["changes"][0]["memoryType"] == "timeline"
    assert dumped["changes"][0]["evidence"]["sourceSpan"]["quote"] == (
        "Lin Jin named the mirror as a witness."
    )
    assert "source_generation_id" not in dumped


def test_exported_memory_extraction_json_schema_uses_camel_case_contract():
    properties = MEMORY_EXTRACTION_RESULT_JSON_SCHEMA["properties"]

    assert "sourceGenerationId" in properties
    assert "source_generation_id" not in properties
    assert "schemaVersion" in properties
    assert "extractorVersion" in properties


def test_memory_change_rejects_blank_reasoning_and_evidence():
    payload = timeline_change()
    payload["reasoning"] = " "

    with pytest.raises(ValidationError):
        MemoryExtractionResult.model_validate(
            base_result_payload(changes=[payload])
        )

    payload = timeline_change()
    payload["evidence"]["quote"] = " "

    with pytest.raises(ValidationError):
        MemoryExtractionResult.model_validate(
            base_result_payload(changes=[payload])
        )


def test_memory_change_rejects_confidence_outside_zero_to_one():
    payload = timeline_change()
    payload["confidence"] = 1.5

    with pytest.raises(ValidationError):
        MemoryExtractionResult.model_validate(
            base_result_payload(changes=[payload])
        )


def test_memory_change_rejects_overlong_source_quote():
    payload = timeline_change()
    payload["evidence"]["sourceSpan"]["quote"] = "x" * 281

    with pytest.raises(ValidationError):
        MemoryExtractionResult.model_validate(
            base_result_payload(changes=[payload])
        )


def test_memory_warning_must_reference_known_change_ids():
    with pytest.raises(ValidationError):
        MemoryExtractionResult.model_validate(
            {
                **base_result_payload(changes=[timeline_change()]),
                "warnings": [
                    {
                        "code": "conflict",
                        "message": "Unknown change reference.",
                        "changeIds": ["missing-change"],
                    }
                ],
            }
        )


def test_foreshadow_update_requires_existing_id():
    payload = foreshadow_change()
    payload["operation"] = "resolve"
    payload["lifecycle"] = "resolved"
    payload["foreshadowId"] = None

    with pytest.raises(ValidationError):
        MemoryExtractionResult.model_validate(
            base_result_payload(changes=[payload])
        )


def base_result_payload(changes):
    return {
        "storyId": "story-1",
        "chapterId": "chapter-3",
        "sourceGenerationId": "generation-1",
        "status": "extracted",
        "summary": "Pending memory changes were extracted.",
        "changes": changes,
    }


def evidence(quote="Lin Jin named the mirror as a witness."):
    return {
        "quote": quote,
        "sourceSpan": {
            "startOffset": 12,
            "endOffset": 48,
            "quote": quote,
        },
    }


def timeline_change():
    return {
        "changeId": "memchg-timeline-1",
        "memoryType": "timeline",
        "operation": "add",
        "confidence": 0.92,
        "evidence": evidence(),
        "reasoning": "This event changes the durable order of the mirror-market plot.",
        "event": "Lin Jin names the mirror as a witness.",
        "order": 2,
        "timing": "chapter 3, after the market search",
        "participants": ["Lin Jin", "Mirror"],
        "consequence": "Future chapters must treat the mirror as a named witness.",
    }


def character_change():
    return {
        "changeId": "memchg-character-1",
        "memoryType": "character",
        "operation": "update",
        "confidence": 0.88,
        "evidence": evidence("Lin Jin admits he knows the betrayer's true name."),
        "reasoning": "The protagonist gains durable knowledge that affects future choices.",
        "character": {"name": "Lin Jin", "memoryId": "char-lin-jin"},
        "changeKind": "knowledge",
        "before": "He only suspected the betrayer.",
        "after": "He knows the betrayer's true name.",
        "impact": "Future scenes should not treat the betrayer's identity as unknown to him.",
    }


def world_change():
    return {
        "changeId": "memchg-world-1",
        "memoryType": "world",
        "operation": "add",
        "confidence": 0.81,
        "evidence": evidence("The mirror market accepts true names as binding oaths."),
        "reasoning": "This establishes a reusable rule for the market.",
        "subjectType": "rule",
        "subject": "Mirror market oaths",
        "description": "True names can bind testimony in the mirror market.",
        "scope": "story",
        "impact": "Later market scenes must respect the oath rule.",
    }


def foreshadow_change():
    return {
        "changeId": "memchg-foreshadow-1",
        "memoryType": "foreshadow",
        "operation": "add",
        "confidence": 0.76,
        "evidence": evidence("The cracked reflection repeats one name three times."),
        "reasoning": "The repeated name is a planted clue for a later payoff.",
        "lifecycle": "planted",
        "content": "A cracked reflection repeats the betrayer's name three times.",
        "relatedCharacters": ["Lin Jin"],
        "payoffHint": "The repeated name can identify the betrayer's hidden avatar.",
    }
