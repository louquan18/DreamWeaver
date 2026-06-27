"""Prompt builder for extracting pending memory changes from confirmed chapter text."""

# ruff: noqa: E501

import json
from dataclasses import dataclass, field
from typing import Any

from src.schemas.memory import MemoryExtractionResult

MEMORY_EXTRACTION_SYSTEM_PROMPT = """You are DreamWeaver's Memory Extraction Agent.

Your task is to extract pending structured memory changes from an already confirmed chapter draft. The draft has passed the user's draft-confirmation step; however, the extracted memories are still pending human review and must not be treated as committed long-term memory yet.

Hard rules:
- Input is a confirmed chapter draft, not an unconfirmed draft or outline.
- Extract only changes that are directly supported by evidence in the confirmedDraft text.
- Do not invent facts, fill missing lore, summarize unsupported intent, or promote blueprint/outline ideas that did not appear in the confirmedDraft.
- Use blueprint, confirmedOutline, recentChapters, and existingMemory only as context for identity, continuity, and conflict detection.
- Return exactly one JSON object. Do not return Markdown, code fences, comments, explanations, or extra text.
- Use camelCase field names.
- The JSON object must align with the MemoryExtractionResult / MemoryChangeSet contract described below.

Top-level JSON contract:
{
  "storyId": "string",
  "chapterId": "string",
  "sourceGenerationId": "string",
  "status": "extracted|partial|blocked",
  "summary": "short human-readable extraction summary",
  "changes": [
    {
      "changeId": "stable id such as memchg-001",
      "memoryType": "timeline|character|world|foreshadow",
      "operation": "add|update|resolve|deprecate",
      "confidence": 0.0,
      "evidence": {
        "quote": "short quote or exact paraphrase from confirmedDraft",
        "sourceSpan": {
          "startOffset": 0,
          "endOffset": 42,
          "quote": "exact supporting text"
        }
      },
      "reasoning": "why this should become pending memory",
      "notes": "optional reviewer-facing note",
      "blockingHints": ["conflict or ambiguity that may block confirmation"],
      "conflictHints": ["possible conflict with existing memory"],
      "...typeSpecificPayload": {}
    }
  ],
  "warnings": [
    {
      "code": "low_confidence|conflict|insufficient_evidence|ambiguous_identity|duplicate_candidate",
      "message": "reviewer-facing warning",
      "changeIds": ["memchg-001"]
    }
  ]
}

Common change requirements:
- changeId must be stable within the result.
- memoryType must be one of timeline, character, world, foreshadow.
- operation must be one of add, update, resolve, deprecate.
- confidence must be between 0 and 1.
- evidence.sourceSpan.startOffset and evidence.sourceSpan.endOffset must point into confirmedDraft when offsets are available; if exact offsets are unavailable, set both to null and provide a quote.
- Use blockingHints for unresolved ambiguity that requires human review.
- Use conflictHints when the change may contradict existingMemory, blueprint.lockedFacts, or confirmedOutline.
- Low-confidence or conflicting changes must stay in changes with warnings; do not pretend they are certain facts.

Timeline payload:
- event: clear event text.
- order: chapter-local order number.
- timing: temporal marker such as before/after/during, chapter number, or scene reference.
- participants: non-empty list of involved character/entity names.
- consequence: why the event matters for later continuity.

Character payload:
- character: object containing name and optional existing memory id/alias.
- changeKind: identity|state|motivation|relationship|knowledge|ability.
- before: known prior state when available.
- after: new state supported by confirmedDraft.
- relatedCharacters: optional list for relationship changes.
- impact: why future chapters need this memory.

World payload:
- subjectType: rule|location|artifact|faction|system.
- subject: name of the world element.
- description: supported world fact or changed setting.
- scope: local|story|global.
- impact: continuity implication.

Foreshadow payload:
- foreshadowId: existing id when updating/resolving/deprecating; null for new planned/planted hints.
- lifecycle: planned|planted|strengthened|triggered|resolved|abandoned.
- content: clue, promise, trigger, or payoff.
- relatedCharacters: optional list.
- relatedItems: optional list.
- relatedLocations: optional list.
- payoffHint: optional future payoff direction.
"""


MEMORY_EXTRACTION_HUMAN_PROMPT = """Extract pending memory changes from the confirmed chapter draft below.

Metadata:
{metadata}

Story:
{story}

Chapter:
{chapter}

Confirmed blueprint:
{blueprint}

Confirmed outline:
{confirmed_outline}

Recent chapters:
{recent_chapters}

Existing memory context:
{existing_memory}

Generation metadata:
{generation_metadata}

Review metadata:
{review_metadata}

Consistency metadata:
{consistency_metadata}

Repair metadata:
{repair_metadata}

Confirmed draft:
{confirmed_draft}

Return only MemoryExtractionResult JSON.
"""


RECENT_CHAPTER_COMPRESSION_RULES = """

Recent chapter compression rules:
- contextRole="recent_full_text" entries can provide immediate continuity, but new memory changes still require evidence from confirmedDraft.
- contextRole="recent_summary" entries are compressed background; use summary only to avoid duplicates or conflicts with existing history.
- Do not extract or update memory from a recent chapter summary unless confirmedDraft independently supports the change."""


@dataclass(frozen=True)
class MemoryExtractionPromptContext:
    """Inputs for extracting pending memory changes after draft confirmation."""

    story_id: str
    chapter_id: str
    source_generation_id: str
    story: dict[str, Any] = field(default_factory=dict)
    chapter: dict[str, Any] = field(default_factory=dict)
    blueprint: dict[str, Any] = field(default_factory=dict)
    confirmed_outline: dict[str, Any] = field(default_factory=dict)
    recent_chapters: list[dict[str, Any]] = field(default_factory=list)
    existing_memory: dict[str, Any] = field(default_factory=dict)
    generation_metadata: dict[str, Any] = field(default_factory=dict)
    review_metadata: dict[str, Any] = field(default_factory=dict)
    consistency_metadata: dict[str, Any] = field(default_factory=dict)
    repair_metadata: dict[str, Any] = field(default_factory=dict)
    confirmed_draft: str = ""


def build_memory_extraction_messages(
    context: MemoryExtractionPromptContext,
) -> list[dict[str, str]]:
    """Build JSON-only extraction messages for the future memory extraction agent."""
    metadata = {
        "storyId": context.story_id,
        "chapterId": context.chapter_id,
        "sourceGenerationId": context.source_generation_id,
        "inputStatus": "confirmedDraft",
        "outputStatus": "pendingHumanReview",
    }
    return [
        {
            "role": "system",
            "content": (
                MEMORY_EXTRACTION_SYSTEM_PROMPT
                + RECENT_CHAPTER_COMPRESSION_RULES
                + "\nMemoryExtractionResult JSON schema:\n"
                + _json(_schema())
            ),
        },
        {
            "role": "user",
            "content": MEMORY_EXTRACTION_HUMAN_PROMPT.format(
                metadata=_json(metadata),
                story=_json(context.story),
                chapter=_json(context.chapter),
                blueprint=_json(context.blueprint),
                confirmed_outline=_json(context.confirmed_outline),
                recent_chapters=_json(context.recent_chapters),
                existing_memory=_json(_normalize_existing_memory(context.existing_memory)),
                generation_metadata=_json(context.generation_metadata),
                review_metadata=_json(context.review_metadata),
                consistency_metadata=_json(context.consistency_metadata),
                repair_metadata=_json(context.repair_metadata),
                confirmed_draft=context.confirmed_draft,
            ),
        },
    ]


def _schema() -> dict[str, Any]:
    return MemoryExtractionResult.model_json_schema(by_alias=True)


def _normalize_existing_memory(existing_memory: dict[str, Any]) -> dict[str, Any]:
    return {
        "timeline": existing_memory.get("timeline", []),
        "characters": existing_memory.get("characters", {}),
        "world": existing_memory.get("world", existing_memory.get("worldState", {})),
        "foreshadows": existing_memory.get(
            "foreshadows",
            existing_memory.get("foreshadow", []),
        ),
        "additional": existing_memory.get("additional", []),
    }


def _json(value: Any) -> str:
    normalized = {} if value is None else value
    return json.dumps(normalized, ensure_ascii=False, indent=2, sort_keys=True)
