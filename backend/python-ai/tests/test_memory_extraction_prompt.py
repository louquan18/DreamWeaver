import json

from src.services.memory_extraction_prompt import (
    MemoryExtractionPromptContext,
    build_memory_extraction_messages,
)


def test_memory_extraction_prompt_contains_confirmed_draft_and_context():
    messages = build_memory_extraction_messages(memory_prompt_context())
    prompt = "\n".join(message["content"] for message in messages)

    assert "already confirmed chapter draft" in prompt
    assert "confirmedDraft" in prompt
    assert "A betrayed disciple follows dream fire." in prompt
    assert "Trace the mirror market clue." in prompt
    assert "Lin Jin confirmed the mirror name in the market." in prompt
    assert "Dream fire cannot show complete futures." in prompt
    assert "Existing memory context" in prompt
    assert "A mirror token burns near truth." in prompt
    assert "rewrite-pass-1" in prompt


def test_memory_extraction_prompt_requires_json_only_memory_result_contract():
    system_prompt = build_memory_extraction_messages(memory_prompt_context())[0]["content"]

    assert "Return exactly one JSON object" in system_prompt
    assert "Do not return Markdown" in system_prompt
    assert "MemoryExtractionResult / MemoryChangeSet" in system_prompt
    assert "MemoryExtractionResult JSON schema:" in system_prompt
    assert '"storyId"' in system_prompt
    assert '"chapterId"' in system_prompt
    assert '"sourceGenerationId"' in system_prompt
    assert '"status": "extracted|partial|blocked"' in system_prompt
    assert '"changes"' in system_prompt
    assert '"warnings"' in system_prompt
    assert '"$defs"' in system_prompt


def test_memory_extraction_prompt_documents_all_memory_types_and_common_fields():
    system_prompt = build_memory_extraction_messages(memory_prompt_context())[0]["content"]

    assert '"memoryType": "timeline|character|world|foreshadow"' in system_prompt
    assert '"operation": "add|update|resolve|deprecate"' in system_prompt
    assert '"confidence"' in system_prompt
    assert '"evidence"' in system_prompt
    assert '"sourceSpan"' in system_prompt
    assert '"startOffset"' in system_prompt
    assert '"endOffset"' in system_prompt
    assert '"reasoning"' in system_prompt
    assert '"notes"' in system_prompt
    assert '"blockingHints"' in system_prompt
    assert '"conflictHints"' in system_prompt


def test_memory_extraction_prompt_documents_type_specific_payloads():
    system_prompt = build_memory_extraction_messages(memory_prompt_context())[0]["content"]

    assert "Timeline payload" in system_prompt
    assert "event" in system_prompt
    assert "order" in system_prompt
    assert "timing" in system_prompt
    assert "participants" in system_prompt
    assert "consequence" in system_prompt
    assert "Character payload" in system_prompt
    assert "identity|state|motivation|relationship|knowledge|ability" in system_prompt
    assert "World payload" in system_prompt
    assert "rule|location|artifact|faction|system" in system_prompt
    assert "Foreshadow payload" in system_prompt
    assert "planned|planted|strengthened|triggered|resolved|abandoned" in system_prompt


def test_memory_extraction_prompt_rejects_unsupported_memory_and_uses_warnings():
    system_prompt = build_memory_extraction_messages(memory_prompt_context())[0]["content"]

    assert "Extract only changes that are directly supported by evidence" in system_prompt
    assert "Do not invent facts" in system_prompt
    assert (
        "Use blueprint, confirmedOutline, recentChapters, and existingMemory only as context"
        in system_prompt
    )
    assert (
        "Low-confidence or conflicting changes must stay in changes with warnings"
        in system_prompt
    )
    assert "do not pretend they are certain facts" in system_prompt
    assert "blockingHints" in system_prompt
    assert "conflictHints" in system_prompt
    assert "Recent chapter compression rules" in system_prompt
    assert 'contextRole="recent_full_text"' in system_prompt
    assert 'contextRole="recent_summary"' in system_prompt


def test_memory_extraction_prompt_metadata_is_machine_readable():
    human_prompt = build_memory_extraction_messages(memory_prompt_context())[1]["content"]
    metadata = _extract_json_block(human_prompt, "Metadata:", "Story:")

    assert metadata == {
        "chapterId": "chapter-1",
        "inputStatus": "confirmedDraft",
        "outputStatus": "pendingHumanReview",
        "sourceGenerationId": "generation-1",
        "storyId": "story-1",
    }


def test_memory_extraction_prompt_includes_generation_review_consistency_and_repair_metadata():
    human_prompt = build_memory_extraction_messages(memory_prompt_context())[1]["content"]

    generation_metadata = _extract_json_block(
        human_prompt,
        "Generation metadata:",
        "Review metadata:",
    )
    review_metadata = _extract_json_block(
        human_prompt,
        "Review metadata:",
        "Consistency metadata:",
    )
    consistency_metadata = _extract_json_block(
        human_prompt,
        "Consistency metadata:",
        "Repair metadata:",
    )
    repair_metadata = _extract_json_block(
        human_prompt,
        "Repair metadata:",
        "Confirmed draft:",
    )

    assert generation_metadata == {"modelProfile": "writer-default"}
    assert review_metadata == {"score": 0.82}
    assert consistency_metadata == {"issues": ["mirror-memory-conflict"]}
    assert repair_metadata == {"passId": "rewrite-pass-1"}


def memory_prompt_context() -> MemoryExtractionPromptContext:
    return MemoryExtractionPromptContext(
        story_id="story-1",
        chapter_id="chapter-1",
        source_generation_id="generation-1",
        story={"id": "story-1", "title": "Dream Fire"},
        chapter={"id": "chapter-1", "chapterNumber": 3, "title": "The Mirror Market"},
        blueprint={
            "premise": "A betrayed disciple follows dream fire.",
            "lockedFacts": [{"text": "Dream fire cannot show complete futures."}],
        },
        confirmed_outline={
            "finalOutline": {
                "chapterGoal": "Trace the mirror market clue.",
                "endingHook": "The mirror names the betrayer.",
            }
        },
        recent_chapters=[
            {"chapterNumber": 2, "summary": "Lin Jin escaped the outer sect."}
        ],
        existing_memory={
            "timeline": [{"memoryId": "tl-1", "event": "Lin Jin fled the sect."}],
            "foreshadow": [{"memoryId": "fs-1", "content": "A mirror token burns near truth."}],
        },
        generation_metadata={"modelProfile": "writer-default"},
        review_metadata={"score": 0.82},
        consistency_metadata={"issues": ["mirror-memory-conflict"]},
        repair_metadata={"passId": "rewrite-pass-1"},
        confirmed_draft=(
            "Lin Jin confirmed the mirror name in the market. "
            "The dream fire showed only a fractured symbol, never the whole future."
        ),
    )


def _extract_json_block(content: str, start_label: str, end_label: str) -> dict:
    start = content.index(start_label) + len(start_label)
    end = content.index(end_label)
    return json.loads(content[start:end].strip())
