"""Chapter outline options generation service."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from loguru import logger
from pydantic import ValidationError

from src.models.provider import get_agent_llm
from src.schemas.outline import ChapterOutlineOptionsDraft
from src.services.outline_context import build_outline_options_context
from src.services.outline_prompt import OutlineOptionsPromptContext, build_outline_options_prompt

LLMInvoker = Callable[[list[Any]], Awaitable[str]]


class OutlineGenerationError(RuntimeError):
    """Raised when the LLM response cannot be converted to valid outline options."""


async def generate_outline_options(
    context: OutlineOptionsPromptContext | None = None,
    *,
    story: Any | None = None,
    chapter: Any | None = None,
    story_id: str | None = None,
    chapter_id: str | None = None,
    option_group_id: str | None = None,
    blueprint: Any | None = None,
    author_intent: Any | None = None,
    recent_chapters: Any | None = None,
    timeline: Any | None = None,
    characters: Any | None = None,
    world: Any | None = None,
    foreshadows: Any | None = None,
    additional_memory: Any | None = None,
    llm: Any | LLMInvoker | None = None,
) -> ChapterOutlineOptionsDraft:
    """Generate A/B/C chapter outline options from loaded story context."""
    prompt_context = context or build_outline_options_context(
        story=story,
        chapter=chapter,
        story_id=story_id,
        chapter_id=chapter_id,
        option_group_id=option_group_id,
        blueprint=blueprint,
        author_intent=author_intent,
        recent_chapters=recent_chapters,
        timeline=timeline,
        characters=characters,
        world=world,
        foreshadows=foreshadows,
        additional_memory=additional_memory,
    )

    logger.info(
        "[Outline Agent] Generating outline options: "
        f"story={prompt_context.story_id}, chapter={prompt_context.chapter_id}"
    )
    messages = build_outline_options_prompt(prompt_context)
    content = await _invoke_llm(messages, llm)
    payload = _parse_json_object(content)
    normalized = _normalize_payload(prompt_context, payload)

    try:
        outline_options = ChapterOutlineOptionsDraft.model_validate(normalized)
    except ValidationError as exc:
        raise OutlineGenerationError(
            f"LLM response failed outline schema validation: {_format_schema_errors(exc)}"
        ) from exc
    _validate_c_foreshadow_fallback(prompt_context, outline_options)

    logger.info(
        "[Outline Agent] Outline options generated: "
        f"story={outline_options.story_id}, chapter={outline_options.chapter_id}"
    )
    return outline_options


def _validate_c_foreshadow_fallback(
    context: OutlineOptionsPromptContext,
    outline_options: ChapterOutlineOptionsDraft,
) -> None:
    c_option = next(
        (option for option in outline_options.options if option.option_code == "C"),
        None,
    )
    if c_option is None:
        raise OutlineGenerationError("C foreshadow option is required")

    actions = c_option.foreshadow_actions
    if not actions:
        raise OutlineGenerationError("C option must include at least one foreshadow action")

    existing_ids = {
        str(item.get("id")).strip()
        for item in context.existing_foreshadows
        if isinstance(item, dict) and item.get("id")
    }
    recover_or_strengthen = {"resolve", "trigger", "strengthen"}
    planted_actions = [action for action in actions if action.action == "plant"]
    missing_required_ids = [
        action.action
        for action in actions
        if action.action in recover_or_strengthen and not action.foreshadow_id
    ]
    if missing_required_ids:
        actions_text = ", ".join(sorted(set(missing_required_ids)))
        raise OutlineGenerationError(
            "C option must include foreshadowId when resolving, triggering, "
            f"or strengthening existing foreshadows: {actions_text}"
        )

    referenced_existing = [
        action
        for action in actions
        if action.action in recover_or_strengthen
        and action.foreshadow_id
        and action.foreshadow_id in existing_ids
    ]
    missing_references = [
        action.foreshadow_id
        for action in actions
        if action.foreshadow_id and action.foreshadow_id not in existing_ids
    ]
    if missing_references:
        missing = ", ".join(sorted(set(missing_references)))
        raise OutlineGenerationError(f"C option references unknown foreshadowId: {missing}")

    if existing_ids:
        if planted_actions:
            raise OutlineGenerationError(
                "C option cannot plant a new foreshadow while existing foreshadows are available"
            )
        if referenced_existing:
            return
        raise OutlineGenerationError(
            "C option must resolve, trigger, or strengthen an existing foreshadow "
            "before planting a new one"
        )

    invalid_without_existing = [
        action.action for action in actions if action.action in recover_or_strengthen
    ]
    if invalid_without_existing:
        actions_text = ", ".join(sorted(set(invalid_without_existing)))
        raise OutlineGenerationError(
            "C option cannot resolve, trigger, or strengthen foreshadow without "
            f"existingForeshadows: {actions_text}"
        )

    if not planted_actions:
        raise OutlineGenerationError(
            "C option must plant a new foreshadow when no existing foreshadows are available"
        )


def _normalize_payload(
    context: OutlineOptionsPromptContext,
    payload: dict[str, Any],
) -> dict[str, Any]:
    normalized = dict(payload)
    normalized["storyId"] = context.story_id
    normalized["chapterId"] = context.chapter_id
    if context.option_group_id:
        normalized["optionGroupId"] = context.option_group_id

    options = normalized.get("options")
    if isinstance(options, list):
        normalized["options"] = [
            _normalize_option_metadata(context, option) for option in options
        ]
    return normalized


def _normalize_option_metadata(
    context: OutlineOptionsPromptContext,
    option: Any,
) -> Any:
    if not isinstance(option, dict):
        return option

    normalized = dict(option)
    normalized["storyId"] = context.story_id
    normalized["chapterId"] = context.chapter_id
    if context.option_group_id:
        normalized["optionGroupId"] = context.option_group_id
    if not normalized.get("charactersInvolved") and not normalized.get("characters_involved"):
        repaired_characters = _infer_characters_involved(context, normalized)
        if repaired_characters:
            normalized["charactersInvolved"] = repaired_characters
    return normalized


def _infer_characters_involved(
    context: OutlineOptionsPromptContext,
    option: dict[str, Any],
) -> list[dict[str, str]]:
    names = _character_names_from_scenes(option.get("sceneOutline") or option.get("scene_outline"))
    if not names:
        names = _character_names_from_memory(context.character_memory)
    if not names:
        protagonist = context.blueprint.get("protagonist")
        if isinstance(protagonist, dict):
            name = _clean_text(protagonist.get("name"))
            if name:
                names = [name]

    repaired = []
    for name in names:
        repaired.append(
            {
                "name": name,
                "role": _infer_character_role(name, context),
                "motivation": _infer_character_motivation(name, context),
                "stateChange": "Participates in the chapter beats established by the generated scene outline.",
            }
        )
    return repaired


def _character_names_from_scenes(scenes: Any) -> list[str]:
    names: list[str] = []
    if not isinstance(scenes, list):
        return names
    for scene in scenes:
        if not isinstance(scene, dict):
            continue
        raw_characters = scene.get("characters")
        if not isinstance(raw_characters, list):
            continue
        for raw_name in raw_characters:
            name = _clean_text(raw_name)
            if name and name not in names:
                names.append(name)
    return names


def _character_names_from_memory(character_memory: list[dict[str, Any]]) -> list[str]:
    names: list[str] = []
    for character in character_memory:
        if not isinstance(character, dict):
            continue
        name = _clean_text(character.get("name") or character.get("id"))
        if name and name not in names:
            names.append(name)
    return names


def _infer_character_role(name: str, context: OutlineOptionsPromptContext) -> str:
    protagonist = context.blueprint.get("protagonist")
    if isinstance(protagonist, dict) and _clean_text(protagonist.get("name")) == name:
        return "protagonist"
    for character in context.character_memory:
        if not isinstance(character, dict):
            continue
        if _clean_text(character.get("name") or character.get("id")) == name:
            return _clean_text(character.get("role")) or "supporting"
    return "participant"


def _infer_character_motivation(name: str, context: OutlineOptionsPromptContext) -> str:
    protagonist = context.blueprint.get("protagonist")
    if isinstance(protagonist, dict) and _clean_text(protagonist.get("name")) == name:
        motivation = _clean_text(
            protagonist.get("motivation")
            or protagonist.get("initialGoal")
            or protagonist.get("initial_goal")
        )
        if motivation:
            return motivation

    for character in context.character_memory:
        if not isinstance(character, dict):
            continue
        if _clean_text(character.get("name") or character.get("id")) == name:
            motivation = _clean_text(
                character.get("motivation")
                or character.get("goal")
                or character.get("state")
            )
            if motivation:
                return motivation
    return "Act on the role already established in the generated scene outline."


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


async def _invoke_llm(messages: list[Any], llm: Any | LLMInvoker | None) -> str:
    runner = llm or get_agent_llm("planner")

    try:
        if callable(runner) and not hasattr(runner, "ainvoke"):
            return await runner(messages)

        response = await runner.ainvoke(messages)
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise TypeError("LLM response content must be a string")
        return content
    except OutlineGenerationError:
        raise
    except Exception as exc:
        raise OutlineGenerationError(f"LLM invocation failed: {exc}") from exc


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            text = text[start : end + 1]

    if not text:
        raise OutlineGenerationError("LLM returned an empty response for outline options")

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise OutlineGenerationError(f"LLM did not return valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise OutlineGenerationError("LLM JSON response must be an object")
    return payload


def _format_schema_errors(exc: ValidationError) -> str:
    messages = []
    for error in exc.errors():
        messages.append(
            f"{_schema_path(error.get('loc', ()))}: "
            f"{error.get('msg', 'invalid outline options schema')}"
        )
    return "; ".join(messages)


def _schema_path(loc: Any) -> str:
    aliases = {
        "story_id": "storyId",
        "chapter_id": "chapterId",
        "option_group_id": "optionGroupId",
        "option_code": "optionCode",
        "option_type": "optionType",
        "title_candidates": "titleCandidates",
        "chapter_goal": "chapterGoal",
        "story_summary": "storySummary",
        "scene_outline": "sceneOutline",
        "characters_involved": "charactersInvolved",
        "highlight_moment": "highlightMoment",
        "foreshadow_actions": "foreshadowActions",
        "memory_references": "memoryReferences",
        "why_this_plan": "whyThisPlan",
        "ending_hook": "endingHook",
        "risk_notes": "riskNotes",
    }
    if not isinstance(loc, tuple):
        return str(loc)

    parts: list[str] = []
    for item in loc:
        if isinstance(item, int) and parts:
            parts[-1] = f"{parts[-1]}[{item}]"
        else:
            parts.append(aliases.get(str(item), str(item)))
    return ".".join(parts)
