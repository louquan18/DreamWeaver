import pytest
from pydantic import ValidationError

from src.schemas.consistency import (
    CONSISTENCY_RULE_JSON_SCHEMA,
    DRAFT_CONSISTENCY_REPORT_JSON_SCHEMA,
    ConsistencyIssue,
    ConsistencyRule,
    DraftConsistencyReport,
)
from src.services.consistency_rules import default_consistency_rules


def test_consistency_rule_serializes_java_style_aliases():
    rule = ConsistencyRule.model_validate(
        {
            "ruleId": "timeline.confirmed-outline-order",
            "domain": "timeline",
            "severity": "P0",
            "description": "Draft must follow the confirmed outline scene order.",
            "requiredContext": ["confirmedOutline.finalOutline.sceneOutline", "draft"],
            "checkHint": "Compare scene order against finalOutline.",
            "repairHint": "Reorder scenes without changing the confirmed outline.",
            "blocking": False,
            "autoRepairRequired": False,
        }
    )

    data = rule.model_dump(by_alias=True)

    assert data["ruleId"] == "timeline.confirmed-outline-order"
    assert data["requiredContext"] == ["confirmedOutline.finalOutline.sceneOutline", "draft"]
    assert data["checkHint"] == "Compare scene order against finalOutline."
    assert data["repairHint"] == "Reorder scenes without changing the confirmed outline."
    assert data["blocking"] is True
    assert data["autoRepairRequired"] is True
    assert "rule_id" not in data
    assert "required_context" not in data
    assert "auto_repair_required" not in data


def test_p0_issue_gates_consistency_report():
    report = DraftConsistencyReport.model_validate(
        {
            "summary": "One world rule contradiction blocks this draft.",
            "checkedRuleIds": ["world.locked-facts.no-contradiction"],
            "issues": [
                {
                    "severity": "P0",
                    "domain": "world",
                    "ruleId": "world.locked-facts.no-contradiction",
                    "message": "Draft contradicts a locked power-system rule.",
                    "evidence": "Locked fact says dream gates require blood; draft opens one with a password.",
                    "suggestion": "Rewrite the gate opening so it uses the locked blood condition.",
                    "location": {
                        "chapterId": "chapter-1",
                        "sceneIndex": 2,
                        "paragraphIndex": 5,
                        "quote": "The gate opened when he spoke the password.",
                    },
                    "sceneIndex": 2,
                    "blocking": False,
                    "autoRepairRequired": False,
                }
            ],
            "blocking": False,
            "autoRepairRequired": False,
        }
    )

    data = report.model_dump(by_alias=True)

    assert report.blocking is True
    assert report.auto_repair_required is True
    assert report.issues[0].blocking is True
    assert report.issues[0].auto_repair_required is True
    assert data["checkedRuleIds"] == ["world.locked-facts.no-contradiction"]
    assert data["issues"][0]["ruleId"] == "world.locked-facts.no-contradiction"
    assert data["issues"][0]["location"]["chapterId"] == "chapter-1"
    assert data["issues"][0]["autoRepairRequired"] is True
    assert "checked_rule_ids" not in data


def test_p1_and_p2_rules_and_issues_default_to_non_blocking():
    for severity in ("P1", "P2"):
        rule = ConsistencyRule.model_validate(
            {
                "ruleId": f"character.state.{severity.lower()}",
                "domain": "character",
                "severity": severity,
                "description": "Character state should remain continuous.",
                "requiredContext": ["recentChapters", "draft"],
                "checkHint": "Check emotional and knowledge continuity.",
                "repairHint": "Adjust reactions to bridge from prior state.",
            }
        )
        issue = ConsistencyIssue.model_validate(
            {
                "severity": severity,
                "domain": "character",
                "ruleId": rule.rule_id,
                "message": "Character knows information not yet learned.",
                "evidence": "Scene 1 mentions a secret before discovery.",
                "suggestion": "Move the knowledge reveal after discovery.",
            }
        )

        assert rule.blocking is False
        assert rule.auto_repair_required is False
        assert issue.blocking is False
        assert issue.auto_repair_required is False


def test_consistency_domain_is_restricted_to_four_supported_domains():
    for domain in ("world", "character", "timeline", "foreshadow"):
        issue = ConsistencyIssue.model_validate(
            {
                "severity": "P2",
                "domain": domain,
                "ruleId": f"{domain}.example",
                "message": "Supported consistency domain.",
                "evidence": "Evidence text.",
                "suggestion": "Suggestion text.",
            }
        )
        assert issue.domain == domain

    with pytest.raises(ValidationError):
        ConsistencyIssue.model_validate(
            {
                "severity": "P2",
                "domain": "style",
                "ruleId": "style.example",
                "message": "Unsupported domain.",
                "evidence": "Evidence text.",
                "suggestion": "Suggestion text.",
            }
        )


def test_consistency_schema_rejects_blank_required_text():
    with pytest.raises(ValidationError):
        ConsistencyRule.model_validate(
            {
                "ruleId": "world.blank",
                "domain": "world",
                "severity": "P1",
                "description": "   ",
                "requiredContext": ["draft"],
                "checkHint": "Check world facts.",
                "repairHint": "Repair world facts.",
            }
        )

    with pytest.raises(ValidationError):
        DraftConsistencyReport.model_validate({"summary": "   "})


def test_default_consistency_rules_cover_all_required_domains_and_gate_p0_rules():
    rules = default_consistency_rules()
    domains = {rule.domain for rule in rules}

    assert domains == {"world", "character", "timeline", "foreshadow"}
    assert len(rules) >= 8
    assert len({rule.rule_id for rule in rules}) == len(rules)

    for rule in rules:
        assert rule.required_context
        assert rule.check_hint
        assert rule.repair_hint
        if rule.severity == "P0":
            assert rule.blocking is True
            assert rule.auto_repair_required is True
        else:
            assert rule.blocking is False
            assert rule.auto_repair_required is False


def test_exported_json_schemas_contain_consistency_contract_fields():
    rule_properties = CONSISTENCY_RULE_JSON_SCHEMA["properties"]
    report_properties = DRAFT_CONSISTENCY_REPORT_JSON_SCHEMA["properties"]

    assert set(rule_properties) >= {
        "ruleId",
        "domain",
        "severity",
        "description",
        "requiredContext",
        "checkHint",
        "repairHint",
        "blocking",
        "autoRepairRequired",
    }
    assert set(report_properties) >= {
        "summary",
        "issues",
        "checkedRuleIds",
        "passedRuleIds",
        "blocking",
        "autoRepairRequired",
    }

    issue_ref = report_properties["issues"]["items"]["$ref"].split("/")[-1]
    issue_properties = DRAFT_CONSISTENCY_REPORT_JSON_SCHEMA["$defs"][issue_ref]["properties"]

    assert set(issue_properties) >= {
        "severity",
        "domain",
        "ruleId",
        "message",
        "evidence",
        "suggestion",
        "location",
        "sceneIndex",
        "blocking",
        "autoRepairRequired",
    }
