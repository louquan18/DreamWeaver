"""Context adapter for P3 chapter outline option prompts."""

from collections.abc import Iterable, Mapping
from typing import Any

from pydantic import BaseModel

from src.memory.schema import Foreshadow
from src.services.outline_prompt import OutlineOptionsPromptContext


def build_outline_options_context(
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
) -> OutlineOptionsPromptContext:
    """Normalize loaded story context into ``OutlineOptionsPromptContext``.

    The adapter is intentionally data-only: callers must provide real, already-loaded
    records. It preserves source identifiers when present and drops blank values rather
    than fabricating replacement data.
    """
    story_data = _as_mapping(story)
    chapter_data = _as_mapping(chapter)
    blueprint_data = _as_mapping(blueprint)

    resolved_story_id = _clean_text(story_id) or _first_text(
        story_data,
        "storyId",
        "story_id",
        "id",
    ) or _first_text(blueprint_data, "storyId", "story_id")
    resolved_chapter_id = _clean_text(chapter_id) or _first_text(
        chapter_data,
        "chapterId",
        "chapter_id",
        "id",
    )

    if not resolved_story_id:
        raise ValueError("story_id is required to build outline options context")
    if not resolved_chapter_id:
        raise ValueError("chapter_id is required to build outline options context")

    chapter_number = _first_int(
        chapter_data,
        "chapterNumber",
        "chapter_number",
        "number",
        "order",
        "sequence",
    )

    return OutlineOptionsPromptContext(
        story_id=resolved_story_id,
        chapter_id=resolved_chapter_id,
        option_group_id=_clean_text(option_group_id),
        chapter_number=chapter_number,
        blueprint=_normalize_blueprint(blueprint_data),
        chapter_intent=_normalize_chapter_intent(
            chapter=chapter_data,
            author_intent=author_intent,
            blueprint=blueprint_data,
        ),
        recent_chapters=_normalize_recent_chapters(recent_chapters),
        timeline_memory=_normalize_items(timeline),
        character_memory=_normalize_characters(characters),
        world_memory=_normalize_world(world),
        existing_foreshadows=_normalize_foreshadows(foreshadows),
        additional_memory=_normalize_additional_memory(story_data, additional_memory),
    )


def _normalize_blueprint(blueprint: Mapping[str, Any]) -> dict[str, Any]:
    if not blueprint:
        return {}
    return _prune(
        {
            "id": _first_text(blueprint, "id", "blueprintId", "blueprint_id"),
            "storyId": _first_text(blueprint, "storyId", "story_id"),
            "sourcePrompt": blueprint.get("sourcePrompt") or blueprint.get("source_prompt"),
            "premise": blueprint.get("premise"),
            "genre": blueprint.get("genre"),
            "tone": blueprint.get("tone"),
            "protagonist": blueprint.get("protagonist"),
            "mainThread": blueprint.get("mainThread") or blueprint.get("main_thread"),
            "coreConflict": blueprint.get("coreConflict") or blueprint.get("core_conflict"),
            "worldSeed": blueprint.get("worldSeed") or blueprint.get("world_seed"),
            "writingPreferences": blueprint.get("writingPreferences")
            or blueprint.get("writing_preferences"),
            "lockedFacts": blueprint.get("lockedFacts") or blueprint.get("locked_facts"),
            "status": blueprint.get("status"),
        }
    ) or {}


def _normalize_chapter_intent(
    *,
    chapter: Mapping[str, Any],
    author_intent: Any | None,
    blueprint: Mapping[str, Any],
) -> dict[str, Any]:
    intent = {
        "chapterId": _first_text(chapter, "chapterId", "chapter_id", "id"),
        "chapterNumber": _first_int(
            chapter,
            "chapterNumber",
            "chapter_number",
            "number",
            "order",
            "sequence",
        ),
        "title": chapter.get("title"),
        "goal": chapter.get("goal") or chapter.get("chapterGoal") or chapter.get("chapter_goal"),
        "summary": chapter.get("summary"),
        "status": chapter.get("status"),
        "mainThread": blueprint.get("mainThread") or blueprint.get("main_thread"),
        "authorIntent": _normalize_freeform(author_intent),
    }
    return _prune(intent) or {}


def _normalize_recent_chapters(chapters: Any | None) -> list[dict[str, Any]]:
    normalized = []
    for chapter in _iter_items(chapters):
        data = _as_mapping(chapter)
        if not data:
            continue
        normalized.append(
            _prune(
                {
                    "chapterId": _first_text(data, "chapterId", "chapter_id", "id"),
                    "chapterNumber": _first_int(
                        data,
                        "chapterNumber",
                        "chapter_number",
                        "number",
                        "order",
                        "sequence",
                    ),
                    "title": data.get("title"),
                    "summary": data.get("summary")
                    or data.get("synopsis")
                    or data.get("compressedSummary")
                    or data.get("compressed_summary"),
                    "status": data.get("status"),
                    "memoryId": _first_text(data, "memoryId", "memory_id", "memoryRef"),
                }
            )
        )
    return [item for item in normalized if item]


def _normalize_characters(characters: Any | None) -> list[dict[str, Any]]:
    normalized = []
    if isinstance(characters, Mapping):
        iterable = characters.items()
    else:
        iterable = ((None, item) for item in _iter_items(characters))

    for name, raw in iterable:
        data = _as_mapping(raw)
        if not data and name:
            data = {"name": name}
        if name and "name" not in data:
            data = {"name": name, **data}
        item = _prune(data)
        if item:
            normalized.append(item)
    return normalized


def _normalize_world(world: Any | None) -> list[dict[str, Any]]:
    data = _as_mapping(world)
    if not data:
        return _normalize_items(world)

    entries: list[dict[str, Any]] = []
    for category, values in (
        ("force", data.get("forces")),
        ("location", data.get("locations")),
        ("rule", data.get("rules")),
    ):
        if isinstance(values, Mapping):
            for name, value in values.items():
                entry = _prune({"type": category, "name": name, "details": value})
                if entry:
                    entries.append(entry)

    if entries:
        return entries

    item = _prune(data)
    return [item] if item else []


def _normalize_foreshadows(foreshadows: Any | None) -> list[dict[str, Any]]:
    normalized = []
    for raw in _iter_items(foreshadows):
        data = _as_mapping(raw)
        if not data:
            continue
        status = _clean_text(data.get("status"))
        if status in Foreshadow.TERMINAL_STATUSES:
            continue
        foreshadow_id = _first_text(data, "id", "foreshadowId", "foreshadow_id")
        if not foreshadow_id:
            continue
        normalized.append(
            _prune(
                {
                    "id": foreshadow_id,
                    "title": data.get("title"),
                    "summary": data.get("summary") or data.get("content"),
                    "content": data.get("content"),
                    "status": status,
                    "importance": data.get("importance"),
                    "chapterPlanted": data.get("chapterPlanted") or data.get("chapter_planted"),
                    "triggerCondition": data.get("triggerCondition")
                    or data.get("trigger_condition"),
                    "plannedPayoffHint": data.get("plannedPayoffHint")
                    or data.get("planned_payoff_hint"),
                    "attentionStatus": data.get("attentionStatus") or data.get("attention_status"),
                    "needsAttention": data.get("needsAttention") or data.get("needs_attention"),
                }
            )
        )
    return [item for item in normalized if item]


def _normalize_additional_memory(
    story: Mapping[str, Any],
    additional_memory: Any | None,
) -> dict[str, Any]:
    additional = _as_mapping(additional_memory)
    story_context = _prune(
        {
            "storyId": _first_text(story, "storyId", "story_id", "id"),
            "title": story.get("title"),
            "status": story.get("status"),
            "genre": story.get("genre"),
        }
    )
    merged = dict(additional)
    if story_context:
        merged.setdefault("story", story_context)
    return _prune(merged) or {}


def _normalize_items(items: Any | None) -> list[dict[str, Any]]:
    normalized = []
    if isinstance(items, Mapping):
        iterable = [_with_mapping_key(key, value) for key, value in items.items()]
    else:
        iterable = _iter_items(items)

    for raw in iterable:
        item = _prune(_as_mapping(raw))
        if item:
            normalized.append(item)
    return normalized


def _normalize_freeform(value: Any | None) -> Any:
    if isinstance(value, str):
        return _clean_text(value)
    if isinstance(value, Mapping | BaseModel):
        return _prune(_as_mapping(value))
    if isinstance(value, Iterable) and not isinstance(value, str | bytes | bytearray):
        return [_normalize_freeform(item) for item in value if _normalize_freeform(item)]
    return value


def _as_mapping(value: Any | None) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, BaseModel):
        return value.model_dump(by_alias=True, exclude_none=True)
    if isinstance(value, Mapping):
        return dict(value)
    if hasattr(value, "__dict__"):
        return dict(vars(value))
    return {}


def _iter_items(value: Any | None) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, Mapping):
        return list(value.values())
    if isinstance(value, Iterable) and not isinstance(value, str | bytes | bytearray):
        return list(value)
    return [value]


def _with_mapping_key(key: Any, value: Any) -> Any:
    if not isinstance(key, str) or not key.strip():
        return value

    data = _as_mapping(value)
    if not data:
        return value
    if _first_text(data, "id", "memoryId", "memory_id", "referenceId"):
        return data
    return {"id": key.strip(), **data}


def _prune(value: Any) -> Any:
    if isinstance(value, Mapping):
        pruned = {}
        for key, item in value.items():
            cleaned = _prune(item)
            if cleaned is not None:
                pruned[key] = cleaned
        return pruned or None
    if isinstance(value, list):
        pruned_list = []
        for item in value:
            cleaned = _prune(item)
            if cleaned is not None:
                pruned_list.append(cleaned)
        return pruned_list or None
    if isinstance(value, tuple | set):
        return _prune(list(value))
    if isinstance(value, str):
        return _clean_text(value)
    return value


def _clean_text(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


def _first_text(data: Mapping[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _clean_text(data.get(key))
        if value:
            return value
    return None


def _first_int(data: Mapping[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = data.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())
    return None
