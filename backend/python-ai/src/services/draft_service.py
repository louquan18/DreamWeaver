"""Draft generation from Java-supplied confirmed writing context."""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any

from pydantic import ValidationError

from src.models.llm_client import llm_stream_with_fallback
from src.models.provider import agent_model_chain, agent_temperature
from src.schemas.draft import (
    DEFAULT_DRAFT_TARGET_WORDS,
    DraftGenerateRequest,
    DraftGenerateResult,
)

DEFAULT_TARGET_WORDS = DEFAULT_DRAFT_TARGET_WORDS

DRAFT_SYSTEM_PROMPT = """你是 DreamWeaver 的正文写作 Agent，只负责根据已确认上下文写正文。

你必须严格遵守 Java 传入的已确认小说蓝图和已确认章节中纲。
这是正文生成阶段，不得调用或模拟 Planner，不得重新规划章节主线。
不得改写 confirmedOutline.finalOutline 中的关键剧情、核心冲突、场景顺序、endingHook 或 blueprint.lockedFacts。
可以在不改变关键剧情的前提下补充细节、环境描写、动作、心理和对话。
正文应围绕已确认中纲扩写成完整章节，默认约 2000 字；如果 targetWords 明确给出，则优先遵守 targetWords。
直接输出正文，不要输出标题、JSON、解释、提纲、分镜说明或作者注。
"""

DRAFT_HUMAN_PROMPT = """请严格按以下 Java 已确认写作上下文生成整章正文。

【小说】
{story}

【目标章节】
{chapter}

【已确认小说蓝图】
{blueprint}

【蓝图硬约束提示】
- premise / mainThread / coreConflict 是本章叙事方向的上位约束。
- protagonist / worldSeed / lockedFacts 必须保持一致，尤其 lockedFacts 不得被推翻。

【已确认章节中纲 confirmedOutline】
{confirmed_outline}

【必须执行的 finalOutline】
{final_outline}

【中纲硬约束提示】
- 必须按 finalOutline 的关键剧情和 sceneOutline 顺序推进。
- 必须抵达 finalOutline 的 endingHook，不得替换为其他结尾钩子。
- 不要新增会覆盖或否定 finalOutline 的重大事件。

【最近章节】
{recent_chapters}

【作者额外提示】
{extra_prompt}

【目标字数】
约 {target_words} 字。允许为完成场景自然浮动，但不要写成短梗概。

请直接输出完整章节正文。"""


RECENT_CHAPTER_COMPRESSION_RULES = """

Recent chapter compression rules:
- contextRole="recent_full_text" entries are the strongest local continuity source; use content for immediate scene, tone, and handoff details.
- contextRole="recent_summary" entries are compressed history; use summary for continuity facts and do not infer missing scene details from it.
- If an older chapter has no summary/content field, treat it as unavailable rather than inventing events."""

STRUCTURED_MEMORY_CONTEXT_PROMPT = """

[structuredTimeline]
{timeline}

[characterStates]
{characters}

[worldFacts]
{world}

[openForeshadows]
{foreshadows}

[additionalMemory]
{additional_memory}

[contextMetadata]
{context_metadata}

Structured memory rules:
- Context priority is confirmedOutline > blueprint.lockedFacts > structured memory > recentChapters > additionalMemory > extraPrompt.
- Do not reset abilities, locations, relationships, injuries, knowledge, or motivations recorded in characterStates.
- Do not violate worldFacts with locked=true.
- openForeshadows with status=triggered, revealed, or needsAttention=true should be considered before planting new hints.
- If recentChapters conflict with structured memory, follow structured memory."""

ADDITIONAL_MEMORY_PRIORITY_RULES = """

Additional memory rules:
- additionalMemory is supplemental retrieval material for remote details only.
- It must not override confirmedOutline, blueprint.lockedFacts, or official structured memory.
- If additionalMemory conflicts with official structured memory, follow official structured memory and keep the conflict visible for review/consistency."""


class DraftGenerationInputError(ValueError):
    """Validation error for Java-supplied generate_draft inputs."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


@dataclass(frozen=True)
class DraftStreamEvent:
    """One stable SSE event produced by the generate_draft task."""

    event: str
    data: dict[str, Any]


def validate_generate_draft_request(request: dict[str, Any]) -> DraftGenerateRequest:
    """Validate and normalize Java-owned context for generate_draft."""
    if not isinstance(request, dict):
        raise DraftGenerationInputError("INVALID_DRAFT_REQUEST", "draft request must be a JSON object")

    if not str(request.get("generationId") or "").strip():
        raise DraftGenerationInputError(
            "GENERATION_ID_REQUIRED",
            "generationId is required for draft generation",
        )
    if not _non_empty_object(request.get("story")):
        raise DraftGenerationInputError("STORY_REQUIRED", "story is required for draft generation")
    if not _non_empty_object(request.get("chapter")):
        raise DraftGenerationInputError("CHAPTER_REQUIRED", "chapter is required for draft generation")
    if not _non_empty_object(request.get("blueprint")):
        raise DraftGenerationInputError(
            "CONFIRMED_BLUEPRINT_REQUIRED",
            "blueprint is required for draft generation",
        )
    if not _non_empty_object(request.get("confirmedOutline")):
        raise DraftGenerationInputError(
            "CONFIRMED_OUTLINE_REQUIRED",
            "confirmedOutline is required for draft generation",
        )
    confirmed_outline = request["confirmedOutline"]
    if not _non_empty_object(confirmed_outline.get("finalOutline")):
        raise DraftGenerationInputError(
            "CONFIRMED_FINAL_OUTLINE_REQUIRED",
            "confirmedOutline.finalOutline is required for draft generation",
        )

    try:
        return DraftGenerateRequest.model_validate(request)
    except ValidationError as exc:
        raise DraftGenerationInputError("INVALID_DRAFT_REQUEST", str(exc)) from exc


def build_confirmed_outline_draft_messages(
    request: DraftGenerateRequest | dict[str, Any],
) -> list[dict[str, str]]:
    """Build the writer messages used by the internal Java-to-Python draft stream."""
    draft_request = _coerce_draft_request(request)
    payload = draft_request.writer_payload()
    confirmed_outline = payload["confirmedOutline"]
    final_outline = confirmed_outline.get("finalOutline") or {}
    target_words = draft_request.target_words
    return [
        {"role": "system", "content": DRAFT_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": DRAFT_HUMAN_PROMPT.format(
                story=_json(payload.get("story")),
                chapter=_json(payload.get("chapter")),
                blueprint=_json(payload.get("blueprint")),
                confirmed_outline=_json(confirmed_outline),
                final_outline=_json(final_outline),
                recent_chapters=_json(payload.get("recentChapters")),
                extra_prompt=payload.get("extraPrompt") or "无",
                target_words=target_words,
            )
            + STRUCTURED_MEMORY_CONTEXT_PROMPT.format(
                timeline=_json(payload.get("timeline")),
                characters=_json(payload.get("characters")),
                world=_json(payload.get("world")),
                foreshadows=_json(payload.get("foreshadows")),
                additional_memory=_json(payload.get("additionalMemory")),
                context_metadata=_json(payload.get("contextMetadata")),
            )
            + ADDITIONAL_MEMORY_PRIORITY_RULES
            + RECENT_CHAPTER_COMPRESSION_RULES,
        },
    ]


async def stream_generate_draft(
    request: DraftGenerateRequest | dict[str, Any],
    *,
    story_id: str,
    chapter_id: str,
) -> AsyncIterator[DraftStreamEvent]:
    """Stream the full generate_draft task as stable SSE-ready events."""
    draft_request = _coerce_draft_request(request)
    draft_parts: list[str] = []

    yield DraftStreamEvent("node_start", {"node": "generate_draft", "progress": 50})
    try:
        async for token in stream_confirmed_outline_draft(draft_request):
            draft_parts.append(token)
            yield DraftStreamEvent("token", {"content": token})
    except Exception as exc:  # noqa: BLE001 - model and transport errors are streamed to Java
        yield DraftStreamEvent("error", {"message": str(exc)})
        return

    draft = "".join(draft_parts)
    result = DraftGenerateResult(
        story_id=story_id,
        chapter_id=chapter_id,
        generation_id=draft_request.generation_id,
        draft=draft,
        word_count=len(draft),
        tokens_streamed=len(draft_parts),
    )
    yield DraftStreamEvent("node_end", {"node": "generate_draft", "progress": 50})
    yield DraftStreamEvent("done", result.sse_payload())


async def generate_draft(
    request: DraftGenerateRequest | dict[str, Any],
    *,
    story_id: str,
    chapter_id: str,
) -> DraftGenerateResult:
    """Run generate_draft to completion and return the stable result payload."""
    draft_request = _coerce_draft_request(request)
    draft_parts: list[str] = []
    async for token in stream_confirmed_outline_draft(draft_request):
        draft_parts.append(token)
    draft = "".join(draft_parts)
    return DraftGenerateResult(
        story_id=story_id,
        chapter_id=chapter_id,
        generation_id=draft_request.generation_id,
        draft=draft,
        word_count=len(draft),
        tokens_streamed=len(draft_parts),
    )


async def stream_confirmed_outline_draft(
    request: DraftGenerateRequest | dict[str, Any],
) -> AsyncIterator[str]:
    """Stream draft tokens using the confirmed outline as the hard writing plan."""
    draft_request = _coerce_draft_request(request)
    messages = build_confirmed_outline_draft_messages(draft_request)
    models = agent_model_chain("draft")
    temperature = agent_temperature("draft")
    async for token in llm_stream_with_fallback(
        messages,
        models=models,
        max_tokens=_max_tokens_for_target(draft_request.target_words),
        temperature=temperature,
    ):
        yield token


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2, sort_keys=True)


def _target_words(value: Any) -> int:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, str):
        try:
            parsed = int(value)
        except ValueError:
            return DEFAULT_TARGET_WORDS
        if parsed > 0:
            return parsed
    return DEFAULT_TARGET_WORDS


def _max_tokens_for_target(target_words: int) -> int:
    # 中文写作通常 token/字波动较大，给足余量但保持在模型客户端默认上限内。
    return max(4096, min(8192, int(target_words * 2.5)))


def _coerce_draft_request(request: DraftGenerateRequest | dict[str, Any]) -> DraftGenerateRequest:
    if isinstance(request, DraftGenerateRequest):
        return request
    return validate_generate_draft_request(request)


def _non_empty_object(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)
