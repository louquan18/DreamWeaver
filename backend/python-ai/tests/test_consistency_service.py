import json

import pytest

from src.schemas.consistency import DraftConsistencyReport
from src.services.consistency_service import (
    ConsistencyCheckError,
    build_consistency_check_messages,
    check_consistency,
    parse_consistency_report,
)


def test_consistency_prompt_contains_rules_context_and_draft():
    messages = build_consistency_check_messages(consistency_request_payload())
    prompt = "\n".join(message["content"] for message in messages)

    assert "world.locked-facts.no-contradiction" in prompt
    assert "character.identity-and-role" in prompt
    assert "timeline.confirmed-outline-order" in prompt
    assert "foreshadow.locked-payoff" in prompt
    assert "A betrayed disciple follows dream fire." in prompt
    assert "Dream fire cannot show complete futures" in prompt
    assert "The mirror speaks." in prompt
    assert "Lin Jin opens the mirror gate with a password." in prompt


@pytest.mark.asyncio
async def test_check_consistency_returns_valid_report(monkeypatch):
    captured = {}

    def fake_agent_model_chain(agent_type):
        captured["agent_type"] = agent_type
        return ["consistency-model"]

    def fake_agent_temperature(agent_type):
        captured["temperature_agent_type"] = agent_type
        return 0.1

    async def fake_llm_invoke(messages, model, max_tokens, temperature):
        captured["messages"] = messages
        captured["model"] = model
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        return json.dumps(valid_report_payload(), ensure_ascii=False)

    monkeypatch.setattr("src.services.consistency_service.agent_model_chain", fake_agent_model_chain)
    monkeypatch.setattr("src.services.consistency_service.agent_temperature", fake_agent_temperature)
    monkeypatch.setattr("src.services.consistency_service.llm_invoke", fake_llm_invoke)

    report = await check_consistency(consistency_request_payload())

    assert isinstance(report, DraftConsistencyReport)
    assert report.summary == "One world contradiction blocks this draft."
    assert report.issues[0].rule_id == "world.locked-facts.no-contradiction"
    assert captured["agent_type"] == "consistency"
    assert captured["temperature_agent_type"] == "consistency"
    assert captured["model"] == "consistency-model"
    assert captured["max_tokens"] == 4096
    assert captured["temperature"] == 0.1
    prompt = "\n".join(message["content"] for message in captured["messages"])
    assert "world.locked-facts.no-contradiction" in prompt
    assert "The mirror speaks." in prompt


def test_p0_issue_gates_report_from_llm_payload():
    report = parse_consistency_report(json.dumps(valid_report_payload()))

    assert report.blocking is True
    assert report.auto_repair_required is True
    assert report.issues[0].blocking is True
    assert report.issues[0].auto_repair_required is True
    dumped = report.model_dump(by_alias=True)
    assert dumped["issues"][0]["ruleId"] == "world.locked-facts.no-contradiction"
    assert dumped["issues"][0]["autoRepairRequired"] is True
    assert "rule_id" not in dumped["issues"][0]


def test_parse_consistency_report_rejects_invalid_json():
    with pytest.raises(ConsistencyCheckError) as exc_info:
        parse_consistency_report("not json")

    assert exc_info.value.code == "INVALID_CONSISTENCY_JSON"


def test_parse_consistency_report_rejects_invalid_schema():
    payload = valid_report_payload()
    payload["issues"][0]["severity"] = "high"

    with pytest.raises(ConsistencyCheckError) as exc_info:
        parse_consistency_report(json.dumps(payload))

    assert exc_info.value.code == "INVALID_CONSISTENCY_REPORT"


@pytest.mark.asyncio
async def test_check_consistency_uses_consistency_model_not_other_agents(monkeypatch):
    requested_agents = []

    def fake_agent_model_chain(agent_type):
        requested_agents.append(agent_type)
        return ["consistency-model"]

    def fake_agent_temperature(agent_type):
        requested_agents.append(f"temperature:{agent_type}")
        return 0.1

    async def fake_llm_invoke(messages, model, max_tokens, temperature):
        return json.dumps({"summary": "No issues.", "issues": [], "checkedRuleIds": [], "passedRuleIds": []})

    monkeypatch.setattr("src.services.consistency_service.agent_model_chain", fake_agent_model_chain)
    monkeypatch.setattr("src.services.consistency_service.agent_temperature", fake_agent_temperature)
    monkeypatch.setattr("src.services.consistency_service.llm_invoke", fake_llm_invoke)

    await check_consistency(consistency_request_payload())

    assert requested_agents == ["consistency", "temperature:consistency"]
    assert "writer" not in requested_agents
    assert "planner" not in requested_agents
    assert "reviewer" not in requested_agents


def test_check_consistency_rejects_missing_required_input():
    payload = consistency_request_payload()
    payload["draft"] = " "

    with pytest.raises(ConsistencyCheckError) as exc_info:
        build_consistency_check_messages(payload)

    assert exc_info.value.code == "DRAFT_REQUIRED"


def test_check_consistency_rejects_missing_final_outline():
    payload = consistency_request_payload()
    payload["confirmedOutline"] = {"id": "outline-1"}

    with pytest.raises(ConsistencyCheckError) as exc_info:
        build_consistency_check_messages(payload)

    assert exc_info.value.code == "CONFIRMED_FINAL_OUTLINE_REQUIRED"


def consistency_request_payload():
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
                ],
                "endingHook": "The mirror speaks.",
                "foreshadowActions": [{"type": "trigger", "detail": "Mirror calls his true name."}],
            },
        },
        "recentChapters": [
            {
                "chapterNumber": 2,
                "title": "Ash Road",
                "content": "Lin Jin escaped with the dream token.",
            }
        ],
        "activeForeshadows": [{"id": "f1", "description": "The mirror knows true names."}],
        "timeline": [{"chapterNumber": 2, "event": "Lin Jin obtained the dream token."}],
        "characters": {"Lin Jin": {"role": "protagonist"}},
        "worldState": {"dreamFire": "cannot show complete futures"},
        "draft": "Lin Jin opens the mirror gate with a password. The mirror speaks.",
    }


def valid_report_payload():
    return {
        "summary": "One world contradiction blocks this draft.",
        "issues": [
            {
                "severity": "P0",
                "domain": "world",
                "ruleId": "world.locked-facts.no-contradiction",
                "message": "The draft contradicts the locked dream fire rule.",
                "evidence": "Draft says Lin Jin opens the mirror gate with a password.",
                "suggestion": "Rewrite the gate opening so it follows the locked dream fire rule.",
                "location": {
                    "chapterId": "chapter-1",
                    "sceneIndex": 1,
                    "paragraphIndex": 0,
                    "quote": "Lin Jin opens the mirror gate with a password.",
                },
                "sceneIndex": 1,
            }
        ],
        "checkedRuleIds": ["world.locked-facts.no-contradiction"],
        "passedRuleIds": ["timeline.confirmed-outline-order"],
        "blocking": False,
        "autoRepairRequired": False,
    }
