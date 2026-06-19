"""Business validation for lightweight novel blueprints."""

import re
from dataclasses import dataclass, field
from typing import Any

from src.schemas.blueprint import BlueprintValidationIssue, NovelBlueprintDraft


@dataclass(frozen=True)
class BlueprintValidationResult:
    """Validation result split into blocking errors and non-blocking warnings."""

    errors: list[BlueprintValidationIssue] = field(default_factory=list)
    warnings: list[BlueprintValidationIssue] = field(default_factory=list)

    @property
    def has_blocking_errors(self) -> bool:
        return bool(self.errors)


class BlueprintValidationError(RuntimeError):
    """Raised when a generated blueprint fails blocking business validation."""

    def __init__(self, errors: list[BlueprintValidationIssue]):
        super().__init__("Generated blueprint failed business validation")
        self.errors = errors


NEGATION_CUES = (
    "不能",
    "不得",
    "不会",
    "不可",
    "禁止",
    "没有",
    "无",
    "不要",
    "避免",
    "拒绝",
    "放弃",
    "not",
    "never",
    "cannot",
    "can't",
    "must not",
    "no ",
    "avoid",
    "abandon",
    "give up",
    "forbid",
    "forbidden",
)

AFFIRMATION_CUES = (
    "必须",
    "可以",
    "会",
    "允许",
    "需要",
    "must",
    "can",
    "will",
    "allow",
    "allowed",
    "requires",
)


def validate_blueprint(blueprint: NovelBlueprintDraft) -> BlueprintValidationResult:
    """Validate required fields and perform conservative conflict screening."""
    errors: list[BlueprintValidationIssue] = []
    warnings: list[BlueprintValidationIssue] = []

    _validate_required_fields(blueprint, errors, warnings)
    _warn_duplicate_locked_facts(blueprint.locked_facts, warnings)
    _warn_locked_fact_conflicts(blueprint, warnings)
    _warn_locked_world_rules_without_facts(blueprint, warnings)
    _warn_protagonist_goal_alignment(blueprint, warnings)

    return BlueprintValidationResult(errors=errors, warnings=warnings)


def _validate_required_fields(
    blueprint: NovelBlueprintDraft,
    errors: list[BlueprintValidationIssue],
    warnings: list[BlueprintValidationIssue],
) -> None:
    if not _non_empty(blueprint.premise):
        errors.append(_error("REQUIRED_FIELD_MISSING", "premise", "premise must not be empty"))

    if not _non_empty(blueprint.protagonist.get("name")):
        errors.append(
            _error(
                "REQUIRED_FIELD_MISSING",
                "protagonist.name",
                "protagonist.name must not be empty",
            )
        )

    if not _non_empty(blueprint.main_thread.get("goal")):
        errors.append(
            _error(
                "REQUIRED_FIELD_MISSING",
                "mainThread.goal",
                "mainThread.goal must not be empty",
            )
        )

    external = blueprint.core_conflict.get("external")
    internal = blueprint.core_conflict.get("internal")
    if not _non_empty(external) and not _non_empty(internal):
        errors.append(
            _error(
                "CORE_CONFLICT_MISSING",
                "coreConflict",
                "coreConflict.external or coreConflict.internal must be present",
            )
        )

    if not _non_empty(blueprint.core_conflict.get("stakes")):
        warnings.append(
            _warning(
                "CORE_CONFLICT_STAKES_MISSING",
                "coreConflict.stakes",
                "coreConflict.stakes is recommended so later chapters know what failure costs",
            )
        )

    rules = blueprint.world_seed.get("rules")
    if not isinstance(rules, list):
        errors.append(
            _error(
                "WORLD_RULES_NOT_ARRAY",
                "worldSeed.rules",
                "worldSeed.rules must be an array",
            )
        )

    for idx, fact in enumerate(blueprint.locked_facts):
        if not isinstance(fact, dict) or not _non_empty(fact.get("text")):
            errors.append(
                _error(
                    "LOCKED_FACT_TEXT_MISSING",
                    f"lockedFacts[{idx}].text",
                    "lockedFacts items must include non-empty text",
                )
            )


def _warn_duplicate_locked_facts(
    locked_facts: list[dict[str, Any]],
    warnings: list[BlueprintValidationIssue],
) -> None:
    seen: dict[str, int] = {}
    for idx, fact in enumerate(locked_facts):
        text = str(fact.get("text", ""))
        key = _normalize_text(text)
        if not key:
            continue
        if key in seen:
            warnings.append(
                _warning(
                    "DUPLICATE_LOCKED_FACT",
                    f"lockedFacts[{idx}].text",
                    f"locked fact duplicates lockedFacts[{seen[key]}].text",
                )
            )
        else:
            seen[key] = idx


def _warn_locked_fact_conflicts(
    blueprint: NovelBlueprintDraft,
    warnings: list[BlueprintValidationIssue],
) -> None:
    avoid_items = blueprint.writing_preferences.get("avoid", [])
    if not isinstance(avoid_items, list):
        return

    comparisons: list[tuple[str, str, str]] = []
    for idx, avoid in enumerate(avoid_items):
        comparisons.append((f"writingPreferences.avoid[{idx}]", str(avoid), "avoid"))

    rules = blueprint.world_seed.get("rules", [])
    if isinstance(rules, list):
        for idx, rule in enumerate(rules):
            if isinstance(rule, dict):
                comparisons.append(
                    (
                        f"worldSeed.rules[{idx}].description",
                        str(rule.get("description", "")),
                        "rule",
                    )
                )

    comparisons.append(("mainThread.goal", str(blueprint.main_thread.get("goal", "")), "goal"))

    for fact_idx, fact in enumerate(blueprint.locked_facts):
        fact_text = str(fact.get("text", ""))
        if not fact_text.strip():
            continue
        for path, other_text, source_kind in comparisons:
            if not other_text.strip():
                continue
            if source_kind == "avoid":
                conflict = _texts_overlap(fact_text, other_text)
            else:
                conflict = _has_obvious_negation_conflict(fact_text, other_text)
            if conflict:
                warnings.append(
                    _warning(
                        "POSSIBLE_BLUEPRINT_CONFLICT",
                        f"lockedFacts[{fact_idx}].text",
                        f"locked fact may conflict with {path}",
                    )
                )


def _warn_locked_world_rules_without_facts(
    blueprint: NovelBlueprintDraft,
    warnings: list[BlueprintValidationIssue],
) -> None:
    rules = blueprint.world_seed.get("rules", [])
    if not isinstance(rules, list):
        return

    fact_texts = [str(fact.get("text", "")) for fact in blueprint.locked_facts]
    for idx, rule in enumerate(rules):
        if not isinstance(rule, dict) or rule.get("locked") is not True:
            continue
        description = str(rule.get("description", ""))
        if not description.strip():
            continue
        if not any(_texts_overlap(description, fact_text) for fact_text in fact_texts):
            warnings.append(
                _warning(
                    "LOCKED_WORLD_RULE_NOT_IN_LOCKED_FACTS",
                    f"worldSeed.rules[{idx}]",
                    "locked world rule is not mirrored in lockedFacts",
                )
            )


def _warn_protagonist_goal_alignment(
    blueprint: NovelBlueprintDraft,
    warnings: list[BlueprintValidationIssue],
) -> None:
    protagonist_goal = str(blueprint.protagonist.get("initialGoal", "")).strip()
    main_goal = str(blueprint.main_thread.get("goal", "")).strip()

    if not protagonist_goal:
        warnings.append(
            _warning(
                "PROTAGONIST_GOAL_MISSING",
                "protagonist.initialGoal",
                "protagonist.initialGoal is recommended for the first chapter direction",
            )
        )
        return

    if main_goal and _has_obvious_negation_conflict(protagonist_goal, main_goal):
        warnings.append(
            _warning(
                "PROTAGONIST_GOAL_MAIN_THREAD_MISMATCH",
                "protagonist.initialGoal",
                "protagonist.initialGoal may conflict with mainThread.goal",
            )
        )


def _error(code: str, path: str, message: str) -> BlueprintValidationIssue:
    return BlueprintValidationIssue(
        code=code,
        path=path,
        message=message,
        severity="error",
        blocking=True,
    )


def _warning(code: str, path: str, message: str) -> BlueprintValidationIssue:
    return BlueprintValidationIssue(
        code=code,
        path=path,
        message=message,
        severity="warning",
        blocking=False,
    )


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _normalize_text(text: str) -> str:
    return re.sub(r"[\W_]+", "", text.lower(), flags=re.UNICODE)


def _has_negation(text: str) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in NEGATION_CUES)


def _has_affirmation(text: str) -> bool:
    lowered = text.lower()
    return any(cue in lowered for cue in AFFIRMATION_CUES)


def _has_obvious_negation_conflict(first: str, second: str) -> bool:
    if not _texts_overlap(first, second):
        return False
    first_negative = _has_negation(first)
    second_negative = _has_negation(second)
    if first_negative == second_negative:
        return False
    return _has_affirmation(first) or _has_affirmation(second) or first_negative or second_negative


def _texts_overlap(first: str, second: str) -> bool:
    first_norm = _normalize_text(first)
    second_norm = _normalize_text(second)
    if not first_norm or not second_norm:
        return False
    if first_norm in second_norm or second_norm in first_norm:
        return True

    first_cjk = _cjk_chars(first)
    second_cjk = _cjk_chars(second)
    if first_cjk and second_cjk:
        shared = first_cjk.intersection(second_cjk)
        smaller = min(len(first_cjk), len(second_cjk))
        return len(shared) >= 4 and len(shared) / max(smaller, 1) >= 0.45

    first_words = set(re.findall(r"[a-z0-9]+", first.lower()))
    second_words = set(re.findall(r"[a-z0-9]+", second.lower()))
    if not first_words or not second_words:
        return False
    shared_words = first_words.intersection(second_words)
    return len(shared_words) >= 2 or any(len(word) >= 5 for word in shared_words)


def _cjk_chars(text: str) -> set[str]:
    return {char for char in text if "\u4e00" <= char <= "\u9fff"}
