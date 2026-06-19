import pytest
from pydantic import ValidationError

from src.schemas.review import (
    DRAFT_QUALITY_REVIEW_JSON_SCHEMA,
    DraftQualityReviewReport,
    ReviewIssue,
)


def test_review_report_serializes_java_style_aliases():
    report = DraftQualityReviewReport.model_validate(
        {
            "overallScore": 82,
            "summary": "Draft is readable, but one timeline beat needs cleanup.",
            "issues": [
                {
                    "severity": "P1",
                    "category": "timeline",
                    "message": "The arrival happens before the character learns the route.",
                    "evidence": "Scene 2 places the character at the harbor before the clue scene.",
                    "suggestion": "Move the clue discovery before the harbor arrival.",
                    "sceneIndex": 1,
                    "location": {
                        "chapterId": "chapter-1",
                        "sceneIndex": 1,
                        "paragraphIndex": 3,
                        "quote": "He reached the harbor with no map.",
                    },
                }
            ],
            "revisionHints": ["Reorder the clue and harbor scenes."],
            "strengths": ["The closing hook is strong."],
        }
    )

    data = report.model_dump(by_alias=True)

    assert data["overallScore"] == 82
    assert data["autoRepairRequired"] is False
    assert data["revisionHints"] == ["Reorder the clue and harbor scenes."]
    assert data["issues"][0]["sceneIndex"] == 1
    assert data["issues"][0]["location"]["chapterId"] == "chapter-1"
    assert data["issues"][0]["location"]["paragraphIndex"] == 3
    assert "overall_score" not in data
    assert "revision_hints" not in data


def test_p0_issue_forces_blocking_and_auto_repair_required():
    report = DraftQualityReviewReport.model_validate(
        {
            "overall_score": 41,
            "summary": "A continuity break blocks publishing.",
            "issues": [
                {
                    "severity": "P0",
                    "category": "continuity",
                    "message": "The protagonist dies and then speaks in the next scene.",
                    "evidence": "Scene 3 says she is dead; Scene 4 gives her dialogue.",
                    "suggestion": "Rewrite Scene 4 or make the death a false report.",
                    "blocking": False,
                    "autoRepairRequired": False,
                }
            ],
            "blocking": False,
            "autoRepairRequired": False,
        }
    )

    assert report.blocking is True
    assert report.auto_repair_required is True
    assert report.issues[0].blocking is True
    assert report.issues[0].auto_repair_required is True


def test_p1_and_p2_issues_default_to_non_blocking():
    for severity in ("P1", "P2"):
        issue = ReviewIssue.model_validate(
            {
                "severity": severity,
                "category": "style",
                "message": "Sentence rhythm is repetitive.",
                "evidence": "Three consecutive paragraphs start the same way.",
                "suggestion": "Vary paragraph openings.",
            }
        )

        assert issue.blocking is False
        assert issue.auto_repair_required is False


def test_review_issue_category_is_restricted_to_supported_quality_axes():
    supported_categories = {
        "plot",
        "character",
        "world",
        "timeline",
        "foreshadow",
        "style",
        "pacing",
        "continuity",
    }

    for category in supported_categories:
        issue = ReviewIssue.model_validate(
            {
                "severity": "P2",
                "category": category,
                "message": f"{category} issue",
                "evidence": "Evidence text.",
                "suggestion": "Suggestion text.",
            }
        )
        assert issue.category == category

    with pytest.raises(ValidationError):
        ReviewIssue.model_validate(
            {
                "severity": "P2",
                "category": "grammar",
                "message": "Unsupported category.",
                "evidence": "Evidence text.",
                "suggestion": "Suggestion text.",
            }
        )


def test_review_report_rejects_blank_required_text():
    with pytest.raises(ValidationError):
        DraftQualityReviewReport.model_validate(
            {
                "overallScore": 75,
                "summary": "   ",
                "issues": [],
            }
        )


def test_exported_json_schema_contains_review_gate_fields():
    properties = DRAFT_QUALITY_REVIEW_JSON_SCHEMA["properties"]

    assert set(properties) >= {
        "overallScore",
        "summary",
        "issues",
        "blocking",
        "autoRepairRequired",
        "revisionHints",
        "strengths",
    }

    issue_ref = properties["issues"]["items"]["$ref"].split("/")[-1]
    issue_properties = DRAFT_QUALITY_REVIEW_JSON_SCHEMA["$defs"][issue_ref]["properties"]

    assert set(issue_properties) >= {
        "severity",
        "category",
        "message",
        "evidence",
        "suggestion",
        "location",
        "sceneIndex",
        "blocking",
        "autoRepairRequired",
    }
