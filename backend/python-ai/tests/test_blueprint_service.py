import json

import pytest

from src.schemas.blueprint import LightBlueprintGenerateRequest
from src.services.blueprint_service import BlueprintGenerationError, generate_light_blueprint
from src.services.blueprint_validation import BlueprintValidationError


class FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    async def __call__(self, messages):
        self.messages = messages
        return self.content


def _valid_payload():
    return {
        "premise": "被宗门背叛的少年借梦境预知改写命运。",
        "genre": "xianxia",
        "tone": "热血爽文",
        "protagonist": {
            "name": "林烬",
            "identity": "外门弟子",
            "initialGoal": "活下来并查清背叛真相",
        },
        "main_thread": {
            "goal": "复仇并揭开梦境来源",
            "stages": [{"order": 1, "name": "逃出生天", "goal": "摆脱追杀"}],
        },
        "core_conflict": {
            "external": "宗门追杀",
            "internal": "复仇是否会吞噬底线",
            "stakes": "失败会失去自由并暴露梦境能力",
        },
        "world_seed": {
            "rules": [
                {
                    "id": "world-rule-001",
                    "description": "梦境预知只能看到碎片",
                    "locked": True,
                }
            ]
        },
        "writing_preferences": {"pace": "fast", "style": "爽点密集", "avoid": ["无意义水文"]},
        "locked_facts": ["梦境预知不能保证完全准确"],
    }


@pytest.mark.asyncio
async def test_generate_light_blueprint_with_fake_llm():
    request = LightBlueprintGenerateRequest(
        source_prompt="我想写一个被宗门背叛的少年靠梦境预知复仇的修仙文。",
        genre="xianxia",
        tone="热血爽文",
        target_words=300000,
    )
    fake_llm = FakeLLM(json.dumps(_valid_payload(), ensure_ascii=False))

    blueprint = await generate_light_blueprint("story-1", request, llm=fake_llm)

    assert blueprint.story_id == "story-1"
    assert blueprint.status == "generated"
    assert blueprint.genre == "xianxia"
    assert blueprint.protagonist["name"] == "林烬"
    assert blueprint.main_thread["goal"] == "复仇并揭开梦境来源"
    assert blueprint.writing_preferences["targetWords"] == 300000
    assert blueprint.locked_facts[0]["text"] == "梦境预知不能保证完全准确"
    assert fake_llm.messages is not None


@pytest.mark.asyncio
async def test_generate_light_blueprint_uses_streaming_model_chain_by_default(monkeypatch):
    captured = {}
    raw_json = json.dumps(_valid_payload(), ensure_ascii=False)

    def fake_agent_model_chain(agent_type):
        captured["agent_type"] = agent_type
        return ["blueprint-model"]

    def fake_agent_temperature(agent_type):
        captured["temperature_agent_type"] = agent_type
        return 0.4

    async def fake_llm_stream_with_fallback(messages, models, max_tokens, temperature):
        captured["messages"] = messages
        captured["models"] = models
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        yield raw_json

    monkeypatch.setattr(
        "src.services.blueprint_service.agent_model_chain",
        fake_agent_model_chain,
    )
    monkeypatch.setattr(
        "src.services.blueprint_service.agent_temperature",
        fake_agent_temperature,
    )
    monkeypatch.setattr(
        "src.services.blueprint_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    request = LightBlueprintGenerateRequest(source_prompt="A betrayed disciple seeks revenge")
    blueprint = await generate_light_blueprint("story-1", request)

    assert blueprint.status == "generated"
    assert captured["agent_type"] == "blueprint"
    assert captured["temperature_agent_type"] == "blueprint"
    assert captured["models"] == ["blueprint-model"]
    assert captured["max_tokens"] == 8192
    assert captured["temperature"] == 0.4
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_generate_light_blueprint_rejects_invalid_json():
    request = LightBlueprintGenerateRequest(source_prompt="一个赛博修仙故事")

    with pytest.raises(BlueprintGenerationError):
        await generate_light_blueprint("story-1", request, llm=FakeLLM("not json"))


@pytest.mark.asyncio
async def test_generate_light_blueprint_rejects_business_invalid_blueprint():
    request = LightBlueprintGenerateRequest(source_prompt="A betrayed disciple seeks revenge")
    payload = _valid_payload()
    payload["protagonist"] = {"identity": "outer disciple"}

    with pytest.raises(BlueprintValidationError) as exc_info:
        await generate_light_blueprint(
            "story-1",
            request,
            llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
        )

    assert exc_info.value.errors[0].code == "REQUIRED_FIELD_MISSING"
    assert exc_info.value.errors[0].path == "protagonist.name"


@pytest.mark.asyncio
async def test_generate_light_blueprint_rejects_non_array_locked_facts():
    request = LightBlueprintGenerateRequest(source_prompt="A betrayed disciple seeks revenge")
    payload = _valid_payload()
    payload["locked_facts"] = "not-array"

    with pytest.raises(BlueprintValidationError) as exc_info:
        await generate_light_blueprint(
            "story-1",
            request,
            llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
        )

    assert exc_info.value.errors[0].code == "LOCKED_FACTS_NOT_ARRAY"
    assert exc_info.value.errors[0].path == "lockedFacts"
