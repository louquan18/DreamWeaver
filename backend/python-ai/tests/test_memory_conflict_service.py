from copy import deepcopy

from src.schemas.memory import MemoryExtractionResult
from src.services.memory_conflict_service import detect_memory_conflicts


def test_detect_memory_conflicts_preserves_clean_result_without_new_warnings():
    result = MemoryExtractionResult.model_validate(
        base_result_payload(changes=[timeline_change()])
    )

    detected = detect_memory_conflicts(
        result,
        {
            "existingMemory": {
                "timeline": [{"memoryId": "tl-1", "event": "Lin Jin fled the sect."}],
                "world": [{"memoryId": "world-1", "subject": "Outer sect gates"}],
                "foreshadows": [{"foreshadowId": "fs-1", "content": "A mirror clue waits."}],
            },
            "blueprint": {
                "lockedFacts": [
                    {
                        "text": "Dream fire cannot show complete futures.",
                        "forbiddenTerms": ["complete future"],
                    }
                ]
            },
        },
    )

    assert detected == result
    assert detected.warnings == []
    assert detected.changes[0].conflict is False
    assert detected.changes[0].blocking is False


def test_duplicate_timeline_world_and_foreshadow_candidates_add_nonblocking_warnings():
    result = MemoryExtractionResult.model_validate(
        base_result_payload(
            changes=[
                timeline_change(),
                world_change(),
                foreshadow_change(),
            ]
        )
    )

    detected = detect_memory_conflicts(
        result,
        {
            "existingMemory": {
                "timeline": [
                    {
                        "memoryId": "tl-1",
                        "event": "Lin Jin names the mirror as a witness.",
                    }
                ],
                "world": [
                    {
                        "memoryId": "world-1",
                        "subject": "Mirror market oaths",
                        "description": "True names bind testimony in the mirror market.",
                    }
                ],
                "foreshadows": [
                    {
                        "foreshadowId": "fs-1",
                        "content": "A cracked reflection repeats the betrayer's name three times.",
                    }
                ],
            }
        },
    )

    duplicate_warnings = [
        warning
        for warning in detected.warnings
        if warning.code == "duplicate_candidate"
    ]
    assert {warning.change_ids[0] for warning in duplicate_warnings} == {
        "memchg-timeline-1",
        "memchg-world-1",
        "memchg-foreshadow-1",
    }
    for change in detected.changes:
        assert change.conflict is True
        assert change.blocking is False
        assert change.conflict_hints[0].severity == "warning"


def test_locked_fact_forbidden_term_marks_blocking_conflict():
    payload = base_result_payload(changes=[world_change()])
    payload["changes"][0]["description"] = (
        "The mirror market can reveal a complete future through true names."
    )
    result = MemoryExtractionResult.model_validate(payload)

    detected = detect_memory_conflicts(
        result,
        {
            "blueprint": {
                "lockedFacts": [
                    {
                        "text": "Dream fire cannot show complete futures.",
                        "forbiddenTerms": ["complete future"],
                    }
                ]
            }
        },
    )

    change = detected.changes[0]
    assert change.conflict is True
    assert change.blocking is True
    assert change.conflict_hints[0].severity == "blocking"
    assert "locked fact" in change.conflict_hints[0].message
    assert "complete future" in change.blocking_hints[0]
    assert detected.warnings[0].code == "conflict"
    assert detected.warnings[0].change_ids == ["memchg-world-1"]


def test_foreshadow_resolve_unknown_id_marks_blocking_conflict():
    payload = base_result_payload(changes=[foreshadow_change()])
    payload["changes"][0]["operation"] = "resolve"
    payload["changes"][0]["lifecycle"] = "resolved"
    payload["changes"][0]["foreshadowId"] = "fs-missing"
    result = MemoryExtractionResult.model_validate(payload)

    detected = detect_memory_conflicts(
        result,
        {"existingMemory": {"foreshadows": [{"foreshadowId": "fs-known"}]}},
    )

    change = detected.changes[0]
    assert change.conflict is True
    assert change.blocking is True
    assert change.conflict_hints[0].severity == "blocking"
    assert "fs-missing" in change.conflict_hints[0].message
    assert detected.warnings[0].code == "conflict"
    assert detected.warnings[0].change_ids == ["memchg-foreshadow-1"]


def test_dict_input_is_validated_into_memory_extraction_result():
    detected = detect_memory_conflicts(
        base_result_payload(changes=[timeline_change()]),
        {"existingMemory": {}},
    )

    assert isinstance(detected, MemoryExtractionResult)
    assert detected.changes[0].change_id == "memchg-timeline-1"


def test_warning_change_ids_reference_known_changes_after_detection():
    result = MemoryExtractionResult.model_validate(
        base_result_payload(changes=[character_change(), world_change()])
    )

    detected = detect_memory_conflicts(
        result,
        {
            "existingMemory": {"characters": [{"memoryId": "char-known", "name": "Ming"}]},
            "blueprint": {
                "lockedFacts": [
                    {
                        "text": "True names cannot reveal complete futures.",
                        "mustNotContain": ["complete future"],
                    }
                ]
            },
        },
    )

    known_change_ids = {change.change_id for change in detected.changes}
    assert detected.warnings
    assert all(
        change_id in known_change_ids
        for warning in detected.warnings
        for change_id in warning.change_ids
    )
    MemoryExtractionResult.model_validate(detected.model_dump(by_alias=True))


def test_character_existing_memory_mapping_values_are_used_for_reference_lookup():
    result = MemoryExtractionResult.model_validate(
        base_result_payload(changes=[character_change()])
    )

    detected = detect_memory_conflicts(
        result,
        {
            "existingMemory": {
                "characters": {
                    "Lin Jin": {
                        "memoryId": "char-missing",
                        "name": "Lin Jin",
                    }
                }
            }
        },
    )

    assert detected.changes[0].conflict is True
    assert detected.changes[0].blocking is False
    assert detected.warnings[0].code == "duplicate_candidate"


def base_result_payload(changes):
    return {
        "storyId": "story-1",
        "chapterId": "chapter-3",
        "sourceGenerationId": "generation-1",
        "status": "extracted",
        "summary": "Pending memory changes were extracted.",
        "changes": deepcopy(changes),
        "warnings": [],
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
        "character": {"name": "Lin Jin", "memoryId": "char-missing"},
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
