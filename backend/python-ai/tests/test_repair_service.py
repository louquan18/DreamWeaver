import json

import pytest

from src.schemas.repair import DraftRepairResult
from src.services.repair_service import (
    RepairGenerationError,
    auto_repair_p0,
    build_repair_messages,
    parse_repair_result,
    p0_repair_issues,
    validate_repair_request,
)


@pytest.mark.asyncio
async def test_auto_repair_noops_without_p0_and_does_not_call_llm(monkeypatch):
    async def fail_if_called(*args, **kwargs):
        raise AssertionError("LLM must not be called when no P0 issues exist")

    monkeypatch.setattr("src.services.repair_service.llm_stream_with_fallback", fail_if_called)

    result = await auto_repair_p0(repair_request_payload(review_severity="P1", consistency_severity="P2"))

    assert result.changed is False
    assert result.repaired_draft == repair_request_payload()["draft"]
    assert result.repaired_issue_ids == []
    assert result.remaining_issue_ids == []


def test_p1_p2_do_not_trigger_auto_repair_even_when_flagged():
    payload = repair_request_payload(review_severity="P1", consistency_severity="P2")
    payload["reviewReport"]["issues"][0]["autoRepairRequired"] = True
    payload["consistencyReport"]["issues"][0]["autoRepairRequired"] = True

    request = validate_repair_request(payload)
    review_issues, consistency_issues = p0_repair_issues(request)

    assert review_issues == []
    assert consistency_issues == []


def test_repair_prompt_contains_p0_issues_context_draft_and_constraints():
    messages = build_repair_messages(repair_request_payload())
    prompt = "\n".join(message["content"] for message in messages)

    assert "originalDraft" in prompt
    assert "Lin Jin opens the mirror gate with a password." in prompt
    assert "P0 review issues to repair" in prompt
    assert "P0 consistency issues to repair" in prompt
    assert "confirmedOutline.finalOutline" in prompt
    assert "The mirror speaks." in prompt
    assert "blueprint.lockedFacts" in prompt
    assert "Dream fire cannot show complete futures" in prompt
    assert "Do not change the confirmed outline" in prompt
    assert "review:p0:0:" in prompt
    assert "consistency:p0:0:" in prompt


@pytest.mark.asyncio
async def test_auto_repair_returns_valid_result_from_llm_json(monkeypatch):
    captured = {}

    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        captured["messages"] = messages
        captured["models"] = models
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        yield json.dumps(valid_repair_result_payload(repair_issue_ids(repair_request_payload())), ensure_ascii=False)

    monkeypatch.setattr(
        "src.services.repair_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    result = await auto_repair_p0(repair_request_payload())

    assert isinstance(result, DraftRepairResult)
    assert result.changed is True
    assert result.strategy == "local"
    assert result.repaired_draft.startswith("Lin Jin followed the dream fire")
    assert captured["models"]
    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert "Dream fire cannot show complete futures" in prompt


def test_parse_repair_result_rejects_invalid_json():
    with pytest.raises(RepairGenerationError) as exc_info:
        parse_repair_result("not json")

    assert exc_info.value.code == "INVALID_REPAIR_JSON"


def test_parse_repair_result_rejects_invalid_schema():
    with pytest.raises(RepairGenerationError) as exc_info:
        parse_repair_result(json.dumps({"repairedDraft": ""}))

    assert exc_info.value.code == "INVALID_REPAIR_SCHEMA"


@pytest.mark.asyncio
async def test_auto_repair_uses_rewrite_model_not_other_agents(monkeypatch):
    requested_agents = []

    def fake_agent_model_chain(agent_type):
        requested_agents.append(agent_type)
        return ["rewrite-model"]

    def fake_agent_temperature(agent_type):
        requested_agents.append(f"temperature:{agent_type}")
        return 0.7

    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        yield json.dumps(valid_repair_result_payload(repair_issue_ids(repair_request_payload())), ensure_ascii=False)

    monkeypatch.setattr("src.services.repair_service.agent_model_chain", fake_agent_model_chain)
    monkeypatch.setattr("src.services.repair_service.agent_temperature", fake_agent_temperature)
    monkeypatch.setattr(
        "src.services.repair_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    await auto_repair_p0(repair_request_payload())

    assert requested_agents == ["rewrite", "temperature:rewrite"]
    assert "writer" not in requested_agents
    assert "planner" not in requested_agents
    assert "reviewer" not in requested_agents
    assert "consistency" not in requested_agents


@pytest.mark.asyncio
async def test_auto_repair_rejects_unknown_repaired_issue_ids(monkeypatch):
    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        yield json.dumps(valid_repair_result_payload(["unknown:p0"]), ensure_ascii=False)

    monkeypatch.setattr(
        "src.services.repair_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    with pytest.raises(RepairGenerationError) as exc_info:
        await auto_repair_p0(repair_request_payload())

    assert exc_info.value.code == "INVALID_REPAIR_ISSUE_IDS"


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("generationId", " "),
        ("story", {}),
        ("chapter", {}),
        ("blueprint", {}),
        ("confirmedOutline", {}),
        ("draft", " "),
    ],
)
def test_validate_repair_request_rejects_missing_required_context(field, value):
    payload = repair_request_payload()
    payload[field] = value

    with pytest.raises(RepairGenerationError) as exc_info:
        validate_repair_request(payload)

    assert exc_info.value.code == "INVALID_REPAIR_REQUEST"


def test_validate_repair_request_rejects_missing_final_outline():
    payload = repair_request_payload()
    payload["confirmedOutline"] = {"id": "outline-1"}

    with pytest.raises(RepairGenerationError) as exc_info:
        validate_repair_request(payload)

    assert exc_info.value.code == "INVALID_REPAIR_REQUEST"


def valid_repair_result_payload(issue_ids=None):
    issue_ids = issue_ids or ["review:p0:0:placeholder", "consistency:p0:0:placeholder"]
    return {
        "generationId": "generation-1",
        "repairedDraft": (
            "Lin Jin followed the dream fire into the mirror market. "
            "The token flared with a broken warning rather than a complete future. "
            "At the mirror stall, the reflection spoke the betrayer's name."
        ),
        "repairSummary": "Replaced the complete-future contradiction with a partial dream-fire warning.",
        "repairedIssueIds": issue_ids,
        "remainingIssueIds": [],
        "strategy": "local",
        "changed": True,
    }


def repair_issue_ids(payload):
    request = validate_repair_request(payload)
    review_issues, consistency_issues = p0_repair_issues(request)
    return [issue["id"] for issue in [*review_issues, *consistency_issues]]


def repair_request_payload(review_severity="P0", consistency_severity="P0"):
    return {
        "generationId": "generation-1",
        "story": {"id": "story-1", "title": "Dream Fire", "genre": "xianxia"},
        "chapter": {"id": "chapter-1", "chapterNumber": 3, "title": "The Mirror Market"},
        "blueprint": {
            "premise": "A betrayed disciple follows dream fire.",
            "protagonist": {"name": "Lin Jin"},
            "worldSeed": {"rules": ["Dream fire cannot show complete futures"]},
            "lockedFacts": [{"text": "Dream fire cannot show complete futures"}],
        },
        "confirmedOutline": {
            "id": "outline-1",
            "finalOutline": {
                "chapterGoal": "Trace the hidden mirror through the market.",
                "sceneOutline": [
                    {"order": 1, "summary": "Lin Jin enters under a false name."},
                    {"order": 2, "summary": "The token burns near a mirror stall."},
                    {"order": 3, "summary": "A reflection names the betrayer."},
                ],
                "endingHook": "The mirror speaks.",
            },
        },
        "recentChapters": [
            {
                "chapterNumber": 2,
                "title": "Ash Road",
                "content": "Lin Jin escaped with the dream token.",
            }
        ],
        "extraPrompt": "Keep the ending quiet and ominous.",
        "maxRepairRounds": 1,
        "draft": (
            "Lin Jin opens the mirror gate with a password. "
            "The dream fire showed every event of tomorrow before the mirror spoke."
        ),
        "reviewReport": {
            "overallScore": 35,
            "summary": "Draft breaks the locked dream-fire rule.",
            "issues": [
                {
                    "severity": review_severity,
                    "category": "world",
                    "message": "Dream fire reveals a complete future.",
                    "evidence": "The draft says the flame showed every event of tomorrow.",
                    "suggestion": "Rewrite the vision so it is partial and ambiguous.",
                    "sceneIndex": 1,
                }
            ],
            "blocking": review_severity == "P0",
            "autoRepairRequired": review_severity == "P0",
        },
        "consistencyReport": {
            "summary": "The draft contradicts one locked fact.",
            "issues": [
                {
                    "severity": consistency_severity,
                    "domain": "world",
                    "ruleId": "world.locked-facts.no-contradiction",
                    "message": "The draft contradicts the locked dream fire rule.",
                    "evidence": "The dream fire showed every event of tomorrow.",
                    "suggestion": "Make the dream fire warning incomplete.",
                    "sceneIndex": 1,
                }
            ],
            "checkedRuleIds": ["world.locked-facts.no-contradiction"],
            "passedRuleIds": [],
            "blocking": consistency_severity == "P0",
            "autoRepairRequired": consistency_severity == "P0",
        },
    }
