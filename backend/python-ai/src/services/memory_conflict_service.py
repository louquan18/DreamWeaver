"""Deterministic conflict detection for extracted pending memory changes."""

from collections.abc import Iterable
from typing import Any

from pydantic import ValidationError

from src.schemas.memory import MemoryExtractionResult


class MemoryConflictDetectionError(RuntimeError):
    """Raised when memory conflict detection cannot validate its inputs or output."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def detect_memory_conflicts(
    result: MemoryExtractionResult | dict[str, Any],
    context: dict[str, Any],
) -> MemoryExtractionResult:
    """Annotate extracted memory changes with deterministic conflict hints."""
    extraction_result = _validate_result(result)
    if not isinstance(context, dict):
        raise MemoryConflictDetectionError(
            "INVALID_MEMORY_CONFLICT_CONTEXT",
            "memory conflict context must be a JSON object",
        )

    payload = extraction_result.model_dump(by_alias=True)
    existing_memory = _dict_or_empty(context.get("existingMemory"))
    blueprint = _dict_or_empty(context.get("blueprint"))
    locked_facts = _list_or_empty(blueprint.get("lockedFacts"))

    for change in payload["changes"]:
        _mark_duplicate_candidates(change, existing_memory)
        _mark_locked_fact_conflicts(change, locked_facts)
        _mark_missing_foreshadow_reference(change, existing_memory)
        _mark_missing_character_reference(change, existing_memory)

    _sync_result_warnings(payload)
    return _validate_result(payload)


def _validate_result(result: MemoryExtractionResult | dict[str, Any]) -> MemoryExtractionResult:
    if isinstance(result, MemoryExtractionResult):
        return result
    try:
        return MemoryExtractionResult.model_validate(result)
    except ValidationError as exc:
        raise MemoryConflictDetectionError(
            "INVALID_MEMORY_EXTRACTION_RESULT",
            f"memory extraction result failed schema validation: {exc}",
        ) from exc


def _mark_duplicate_candidates(
    change: dict[str, Any],
    existing_memory: dict[str, Any],
) -> None:
    memory_type = change.get("memoryType")
    candidates = _existing_items_for_type(existing_memory, str(memory_type or ""))
    for candidate in candidates:
        if _is_duplicate_candidate(change, candidate):
            target = _candidate_target(candidate, fallback=str(memory_type or "memory"))
            _add_conflict_hint(
                change,
                target=target,
                message=f"Possible duplicate of existing {memory_type} memory: {target}.",
                severity="warning",
            )
            return


def _mark_locked_fact_conflicts(
    change: dict[str, Any],
    locked_facts: list[Any],
) -> None:
    change_text = _change_core_text(change)
    normalized_change_text = _normalize_text(change_text)
    if not normalized_change_text:
        return

    for locked_fact in locked_facts:
        fact = _dict_or_empty(locked_fact)
        if not fact:
            continue
        for term in _locked_fact_forbidden_terms(fact):
            normalized_term = _normalize_text(term)
            if normalized_term and normalized_term in normalized_change_text:
                target = str(fact.get("text") or "lockedFact").strip()
                message = (
                    f"Change appears to conflict with locked fact '{target}' "
                    f"by containing forbidden term '{term}'."
                )
                _add_conflict_hint(
                    change,
                    target=target,
                    message=message,
                    severity="blocking",
                )
                _add_blocking_hint(
                    change,
                    f"Locked fact conflict: change contains forbidden term '{term}'.",
                )
                return


def _mark_missing_foreshadow_reference(
    change: dict[str, Any],
    existing_memory: dict[str, Any],
) -> None:
    if change.get("memoryType") != "foreshadow":
        return
    if change.get("operation") not in {"update", "resolve", "deprecate"}:
        return

    foreshadow_id = str(change.get("foreshadowId") or "").strip()
    if not foreshadow_id:
        return

    known_ids = {
        item_id
        for item in _existing_items_for_type(existing_memory, "foreshadow")
        for item_id in _candidate_ids(item)
    }
    if foreshadow_id not in known_ids:
        _add_conflict_hint(
            change,
            target=foreshadow_id,
            message=f"Foreshadow change references unknown foreshadowId '{foreshadow_id}'.",
            severity="blocking",
        )
        _add_blocking_hint(
            change,
            f"Unknown foreshadowId '{foreshadow_id}' must be resolved before saving.",
        )


def _mark_missing_character_reference(
    change: dict[str, Any],
    existing_memory: dict[str, Any],
) -> None:
    if change.get("memoryType") != "character":
        return

    character = _dict_or_empty(change.get("character"))
    memory_id = str(character.get("memoryId") or "").strip()
    if not memory_id:
        return

    known_ids = {
        item_id
        for item in _existing_items_for_type(existing_memory, "character")
        for item_id in _candidate_ids(item)
    }
    if memory_id not in known_ids:
        _add_conflict_hint(
            change,
            target=memory_id,
            message=f"Character change references unknown memoryId '{memory_id}'.",
            severity="warning",
        )


def _sync_result_warnings(payload: dict[str, Any]) -> None:
    known_change_ids = {str(change.get("changeId")) for change in payload["changes"]}
    warnings = payload.setdefault("warnings", [])
    existing_warning_keys = {
        (
            warning.get("code"),
            tuple(warning.get("changeIds") or []),
            warning.get("message"),
        )
        for warning in warnings
        if isinstance(warning, dict)
    }

    for change in payload["changes"]:
        change_id = str(change.get("changeId") or "").strip()
        if change_id not in known_change_ids:
            continue
        hints = _list_or_empty(change.get("conflictHints"))
        for hint in hints:
            hint_data = _dict_or_empty(hint)
            if not hint_data:
                continue
            code = (
                "conflict"
                if hint_data.get("severity") == "blocking"
                else "duplicate_candidate"
                if str(hint_data.get("message") or "").startswith("Possible duplicate")
                else "conflict"
            )
            warning = {
                "code": code,
                "message": str(hint_data.get("message") or "").strip(),
                "changeIds": [change_id],
            }
            key = (warning["code"], tuple(warning["changeIds"]), warning["message"])
            if warning["message"] and key not in existing_warning_keys:
                warnings.append(warning)
                existing_warning_keys.add(key)


def _is_duplicate_candidate(change: dict[str, Any], candidate: dict[str, Any]) -> bool:
    change_type = change.get("memoryType")
    if change_type == "timeline":
        return _same_text(change.get("event"), candidate.get("event")) or _similar_text(
            change.get("event"),
            candidate.get("event"),
        )
    if change_type == "world":
        return _same_text(change.get("subject"), candidate.get("subject")) or _similar_text(
            _join_text(change.get("subject"), change.get("description")),
            _join_text(candidate.get("subject"), candidate.get("description")),
        )
    if change_type == "foreshadow":
        foreshadow_id = str(change.get("foreshadowId") or "").strip()
        candidate_ids = _candidate_ids(candidate)
        return (
            bool(foreshadow_id and foreshadow_id in candidate_ids)
            or _same_text(change.get("content"), candidate.get("content"))
            or _similar_text(change.get("content"), candidate.get("content"))
        )
    if change_type == "character":
        character = _dict_or_empty(change.get("character"))
        memory_id = str(character.get("memoryId") or "").strip()
        return (
            bool(memory_id and memory_id in _candidate_ids(candidate))
            or _same_text(character.get("name"), candidate.get("name"))
        )
    return False


def _existing_items_for_type(
    existing_memory: dict[str, Any],
    memory_type: str,
) -> list[dict[str, Any]]:
    keys_by_type = {
        "timeline": ("timeline",),
        "character": ("characters", "character"),
        "world": ("world", "worldState"),
        "foreshadow": ("foreshadows",),
    }
    items: list[dict[str, Any]] = []
    for key in keys_by_type.get(memory_type, ()):
        value = existing_memory.get(key)
        if isinstance(value, list):
            items.extend(item for item in value if isinstance(item, dict))
        elif isinstance(value, dict):
            dict_values = [item for item in value.values() if isinstance(item, dict)]
            if dict_values:
                items.extend(dict_values)
            else:
                items.append(value)
    return items


def _locked_fact_forbidden_terms(locked_fact: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for key in ("forbiddenTerms", "mustNotContain", "contradicts"):
        value = locked_fact.get(key)
        if isinstance(value, str):
            terms.append(value)
        elif isinstance(value, Iterable):
            terms.extend(str(item) for item in value if str(item).strip())
    return terms


def _change_core_text(change: dict[str, Any]) -> str:
    memory_type = change.get("memoryType")
    if memory_type == "timeline":
        return _join_text(
            change.get("event"),
            change.get("timing"),
            change.get("consequence"),
        )
    if memory_type == "character":
        character = _dict_or_empty(change.get("character"))
        return _join_text(
            character.get("name"),
            change.get("before"),
            change.get("after"),
            change.get("impact"),
        )
    if memory_type == "world":
        return _join_text(
            change.get("subject"),
            change.get("description"),
            change.get("impact"),
        )
    if memory_type == "foreshadow":
        return _join_text(
            change.get("foreshadowId"),
            change.get("content"),
            change.get("payoffHint"),
        )
    return ""


def _add_conflict_hint(
    change: dict[str, Any],
    *,
    target: str,
    message: str,
    severity: str,
) -> None:
    hints = change.setdefault("conflictHints", [])
    hint = {
        "target": target,
        "message": message,
        "severity": severity,
    }
    if hint not in hints:
        hints.append(hint)
    change["conflict"] = True
    if severity == "blocking":
        change["blocking"] = True


def _add_blocking_hint(change: dict[str, Any], message: str) -> None:
    hints = change.setdefault("blockingHints", [])
    if message not in hints:
        hints.append(message)
    change["blocking"] = True


def _candidate_target(candidate: dict[str, Any], *, fallback: str) -> str:
    for key in ("memoryId", "foreshadowId", "id", "subject", "event", "name"):
        value = str(candidate.get(key) or "").strip()
        if value:
            return value
    return fallback


def _candidate_ids(candidate: dict[str, Any]) -> set[str]:
    return {
        value
        for key in ("memoryId", "foreshadowId", "id")
        if (value := str(candidate.get(key) or "").strip())
    }


def _similar_text(left: Any, right: Any) -> bool:
    left_tokens = set(_normalize_text(left).split())
    right_tokens = set(_normalize_text(right).split())
    if not left_tokens or not right_tokens:
        return False
    overlap = len(left_tokens & right_tokens)
    smaller = min(len(left_tokens), len(right_tokens))
    return smaller >= 4 and overlap / smaller >= 0.8


def _same_text(left: Any, right: Any) -> bool:
    normalized_left = _normalize_text(left)
    normalized_right = _normalize_text(right)
    return bool(normalized_left and normalized_left == normalized_right)


def _normalize_text(value: Any) -> str:
    return " ".join(str(value or "").casefold().strip().split())


def _join_text(*values: Any) -> str:
    return " ".join(str(value) for value in values if value)


def _dict_or_empty(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list_or_empty(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []
