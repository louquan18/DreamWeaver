"""Default consistency rules for draft review and repair planning."""

from src.schemas.consistency import ConsistencyRule


DEFAULT_CONSISTENCY_RULES: tuple[ConsistencyRule, ...] = (
    ConsistencyRule(
        ruleId="world.locked-facts.no-contradiction",
        domain="world",
        severity="P0",
        description="Draft must not contradict locked world facts from the confirmed blueprint.",
        requiredContext=["blueprint.lockedFacts", "blueprint.worldSeed", "draft"],
        checkHint="Compare every explicit world rule, faction fact, location fact, and power-system rule against the draft.",
        repairHint="Rewrite the conflicting sentence or scene beat so it obeys lockedFacts without changing the confirmed outline.",
    ),
    ConsistencyRule(
        ruleId="world.setting-continuity",
        domain="world",
        severity="P1",
        description="Draft should preserve established setting details and world-state changes from recent chapters.",
        requiredContext=["blueprint.worldSeed", "recentChapters", "draft"],
        checkHint="Look for location, organization, object, ability, and social-rule drift relative to recent chapters.",
        repairHint="Adjust descriptions and causal explanations to match established setting state.",
    ),
    ConsistencyRule(
        ruleId="character.identity-and-role",
        domain="character",
        severity="P0",
        description="Draft must not swap character identity, role, relationship, or core motivation.",
        requiredContext=["blueprint.protagonist", "confirmedOutline.charactersInvolved", "recentChapters", "draft"],
        checkHint="Verify named characters keep the same identity, allegiance, relationships, and stated motivation.",
        repairHint="Rename, reassign dialogue, or rewrite actions so each character matches their established role.",
    ),
    ConsistencyRule(
        ruleId="character.state-and-voice",
        domain="character",
        severity="P1",
        description="Draft should preserve character emotional state, injuries, knowledge, and voice continuity.",
        requiredContext=["confirmedOutline.charactersInvolved", "recentChapters", "draft"],
        checkHint="Check whether characters know impossible information, recover too quickly, or speak against established voice.",
        repairHint="Revise reactions, dialogue, and internal narration to bridge from the latest known character state.",
    ),
    ConsistencyRule(
        ruleId="timeline.confirmed-outline-order",
        domain="timeline",
        severity="P0",
        description="Draft must follow the confirmed outline scene order and ending hook.",
        requiredContext=["confirmedOutline.finalOutline.sceneOutline", "confirmedOutline.finalOutline.endingHook", "draft"],
        checkHint="Compare draft scene sequence with finalOutline.sceneOutline and verify the ending hook is honored.",
        repairHint="Reorder or rewrite scenes to match the confirmed outline without inventing a new plan.",
    ),
    ConsistencyRule(
        ruleId="timeline.causal-continuity",
        domain="timeline",
        severity="P1",
        description="Draft should keep cause-and-effect continuity with recent chapters and within the chapter.",
        requiredContext=["recentChapters", "confirmedOutline.finalOutline", "draft"],
        checkHint="Find events that occur before their causes, skip required transitions, or undo recent outcomes.",
        repairHint="Add bridging beats or move dependent events after their causes.",
    ),
    ConsistencyRule(
        ruleId="foreshadow.locked-payoff",
        domain="foreshadow",
        severity="P0",
        description="Draft must not resolve, invalidate, or contradict locked foreshadowing before its intended payoff.",
        requiredContext=["blueprint.lockedFacts", "confirmedOutline.finalOutline.foreshadowActions", "recentChapters", "draft"],
        checkHint="Check whether planted foreshadowing is prematurely explained away, contradicted, or paid off incorrectly.",
        repairHint="Remove premature resolution or rewrite the beat as a plant, strengthen, trigger, or resolve action matching the outline.",
    ),
    ConsistencyRule(
        ruleId="foreshadow.outline-actions",
        domain="foreshadow",
        severity="P1",
        description="Draft should execute the foreshadow actions requested by the confirmed outline.",
        requiredContext=["confirmedOutline.finalOutline.foreshadowActions", "draft"],
        checkHint="Verify each requested plant, strengthen, trigger, or resolve action has visible draft evidence.",
        repairHint="Add a concise clue, callback, consequence, or payoff paragraph in the appropriate scene.",
    ),
)


def default_consistency_rules() -> list[ConsistencyRule]:
    """Return fresh model instances for callers that may mutate rule metadata."""

    return [rule.model_copy(deep=True) for rule in DEFAULT_CONSISTENCY_RULES]
