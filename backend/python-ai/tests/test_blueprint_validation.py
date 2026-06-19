from src.schemas.blueprint import NovelBlueprintDraft
from src.services.blueprint_validation import validate_blueprint


def _draft(**overrides):
    payload = {
        "story_id": "story-1",
        "source_prompt": "Write a revenge xianxia story",
        "premise": "A betrayed disciple survives and seeks the truth.",
        "genre": "xianxia",
        "tone": "fast",
        "protagonist": {
            "name": "Lin Yan",
            "initialGoal": "survive and investigate the betrayal",
        },
        "main_thread": {
            "goal": "take revenge and reveal the dream mirror source",
            "stages": [{"order": 1, "name": "Escape", "goal": "leave the sect"}],
        },
        "core_conflict": {
            "external": "sect pursuit",
            "internal": "revenge versus conscience",
            "stakes": "failure means capture",
        },
        "world_seed": {
            "rules": [
                {
                    "id": "world-rule-001",
                    "description": "Disciples cannot fly before foundation establishment",
                    "locked": True,
                }
            ]
        },
        "writing_preferences": {"avoid": ["meaningless filler"]},
        "locked_facts": [
            {
                "id": "fact-001",
                "text": "Disciples cannot fly before foundation establishment",
                "category": "world",
                "source": "agent",
            }
        ],
    }
    payload.update(overrides)
    return NovelBlueprintDraft.model_validate(payload)


def test_validate_blueprint_reports_blocking_required_errors():
    blueprint = _draft(
        protagonist={},
        main_thread={"goal": ""},
        core_conflict={"external": "", "internal": ""},
        world_seed={"rules": "not-array"},
    )

    result = validate_blueprint(blueprint)

    assert result.has_blocking_errors
    assert {issue.code for issue in result.errors} == {
        "REQUIRED_FIELD_MISSING",
        "CORE_CONFLICT_MISSING",
        "WORLD_RULES_NOT_ARRAY",
    }
    assert {issue.path for issue in result.errors} >= {
        "protagonist.name",
        "mainThread.goal",
        "coreConflict",
        "worldSeed.rules",
    }
    assert all(issue.blocking for issue in result.errors)


def test_validate_blueprint_reports_non_blocking_warnings():
    blueprint = _draft(
        protagonist={"name": "Lin Yan", "initialGoal": ""},
        core_conflict={"external": "sect pursuit", "internal": ""},
        world_seed={
            "rules": [
                {
                    "id": "world-rule-001",
                    "description": "Dream prophecy cannot reveal complete thoughts",
                    "locked": True,
                }
            ]
        },
        writing_preferences={"avoid": ["revenge"]},
        locked_facts=[
            {
                "id": "fact-001",
                "text": "The protagonist must take revenge",
                "category": "plot",
                "source": "agent",
            },
            {
                "id": "fact-002",
                "text": "The protagonist must take revenge",
                "category": "plot",
                "source": "agent",
            },
        ],
    )

    result = validate_blueprint(blueprint)

    assert not result.has_blocking_errors
    codes = {issue.code for issue in result.warnings}
    assert "CORE_CONFLICT_STAKES_MISSING" in codes
    assert "PROTAGONIST_GOAL_MISSING" in codes
    assert "POSSIBLE_BLUEPRINT_CONFLICT" in codes
    assert "DUPLICATE_LOCKED_FACT" in codes
    assert "LOCKED_WORLD_RULE_NOT_IN_LOCKED_FACTS" in codes
    assert all(not issue.blocking for issue in result.warnings)


def test_validate_blueprint_warns_on_obvious_goal_mismatch():
    blueprint = _draft(
        protagonist={"name": "Lin Yan", "initialGoal": "must abandon revenge"},
        main_thread={"goal": "take revenge against the sect"},
    )

    result = validate_blueprint(blueprint)

    assert "PROTAGONIST_GOAL_MAIN_THREAD_MISMATCH" in {
        issue.code for issue in result.warnings
    }
