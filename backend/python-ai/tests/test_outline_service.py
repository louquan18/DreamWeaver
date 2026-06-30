import json

import pytest

from src.services.outline_prompt import OutlineOptionsPromptContext
from src.services.outline_service import OutlineGenerationError, generate_outline_options


class FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    async def __call__(self, messages):
        self.messages = messages
        return self.content


def _valid_option(code: str, option_type: str):
    return {
        "storyId": "story-1",
        "chapterId": "chapter-2",
        "optionGroupId": "group-1",
        "optionCode": code,
        "optionType": option_type,
        "titleCandidates": [f"Option {code}"],
        "chapterGoal": f"Advance chapter through option {code}",
        "storySummary": f"Chapter option {code} summary.",
        "sceneOutline": [
            {
                "order": 1,
                "summary": "The protagonist enters the abandoned archive.",
                "purpose": "Open the investigation.",
                "characters": ["Lin Jin"],
                "location": "Archive",
                "outcome": "A hidden token is found.",
            },
            {
                "order": 2,
                "summary": "A rival disciple blocks the exit.",
                "purpose": "Increase pressure.",
                "characters": ["Lin Jin", "Rival Disciple"],
                "location": "Archive Gate",
                "outcome": "The protagonist pays a cost to escape.",
            },
            {
                "order": 3,
                "summary": "The token reacts to dream fire.",
                "purpose": "Connect the scene to the main mystery.",
                "characters": ["Lin Jin"],
                "location": "Outer Sect Path",
                "outcome": "The next clue points to the forbidden valley.",
            },
        ],
        "charactersInvolved": [
            {
                "name": "Lin Jin",
                "role": "protagonist",
                "motivation": "Survive and identify the betrayer.",
                "stateChange": "Moves from fleeing to active investigation.",
            }
        ],
        "conflict": {
            "external": "Sect pursuers close in.",
            "internal": "He doubts whether the dream vision can be trusted.",
            "stakes": "Failure exposes his secret ability.",
        },
        "highlightMoment": "Dream fire reveals a hidden mark on the token.",
        "foreshadowActions": [
            {
                "action": "strengthen" if code == "C" else "plant",
                "description": "The token mark repeats a symbol from earlier clues.",
                "foreshadowId": "fs-1" if code == "C" else None,
            }
        ],
        "memoryReferences": [
            {
                "memoryType": "blueprint",
                "summary": "Dream visions are fragmented and unreliable.",
                "memoryId": "bp-1",
                "relevance": "Keeps the ability constrained.",
            }
        ],
        "whyThisPlan": f"Option {code} uses existing context without changing locked facts.",
        "endingHook": "A masked voice says the protagonist's mother's old name.",
        "riskNotes": ["Do not reveal the masked figure's identity yet."],
    }


def _valid_payload():
    return {
        "storyId": "story-1",
        "chapterId": "chapter-2",
        "optionGroupId": "group-1",
        "options": [
            _valid_option("A", "steady"),
            _valid_option("B", "conflict"),
            _valid_option("C", "foreshadow"),
        ],
    }


def _payload_with_c_action(action: str, foreshadow_id: str | None = "fs-1"):
    payload = _valid_payload()
    payload["options"][2]["foreshadowActions"] = [
        {
            "action": action,
            "description": "C option foreshadow fallback action.",
            "foreshadowId": foreshadow_id,
        }
    ]
    return payload


def _existing_foreshadows(count: int, **extra):
    return [
        {
            "id": f"fs-{index}",
            "summary": f"Existing foreshadow {index}.",
            **extra,
        }
        for index in range(1, count + 1)
    ]


@pytest.mark.asyncio
async def test_generate_outline_options_with_fake_llm():
    fake_llm = FakeLLM(json.dumps(_valid_payload(), ensure_ascii=False))

    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        option_group_id="group-1",
        blueprint={"id": "bp-1", "premise": "A betrayed disciple uses dream visions."},
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
        llm=fake_llm,
    )

    assert result.story_id == "story-1"
    assert result.chapter_id == "chapter-2"
    assert result.option_group_id == "group-1"
    assert [option.option_code for option in result.options] == ["A", "B", "C"]
    assert [option.option_type for option in result.options] == [
        "steady",
        "conflict",
        "foreshadow",
    ]
    assert result.options[2].foreshadow_actions[0].foreshadow_id == "fs-1"
    assert fake_llm.messages is not None


@pytest.mark.asyncio
async def test_generate_outline_options_uses_streaming_model_chain_by_default(monkeypatch):
    captured = {}
    raw_json = json.dumps(_valid_payload(), ensure_ascii=False)

    def fake_agent_model_chain(agent_type):
        captured["agent_type"] = agent_type
        return ["outline-model"]

    def fake_agent_temperature(agent_type):
        captured["temperature_agent_type"] = agent_type
        return 0.5

    async def fake_llm_stream_with_fallback(
        messages,
        models,
        max_tokens,
        temperature,
        model_extra_body=None,
    ):
        captured["messages"] = messages
        captured["models"] = models
        captured["max_tokens"] = max_tokens
        captured["temperature"] = temperature
        captured["deepseek_extra_body"] = model_extra_body("deepseek-v4-pro")
        captured["other_extra_body"] = model_extra_body("openai/gpt-4o")
        yield raw_json

    monkeypatch.setattr(
        "src.services.outline_service.agent_model_chain",
        fake_agent_model_chain,
    )
    monkeypatch.setattr(
        "src.services.outline_service.agent_temperature",
        fake_agent_temperature,
    )
    monkeypatch.setattr(
        "src.services.outline_service.llm_stream_with_fallback",
        fake_llm_stream_with_fallback,
    )

    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        option_group_id="group-1",
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
    )

    assert [option.option_code for option in result.options] == ["A", "B", "C"]
    assert captured["agent_type"] == "outline"
    assert captured["temperature_agent_type"] == "outline"
    assert captured["models"] == ["outline-model"]
    assert captured["max_tokens"] == 8192
    assert captured["temperature"] == 0.5
    assert captured["deepseek_extra_body"] == {"thinking": {"type": "disabled"}}
    assert captured["other_extra_body"] is None
    assert captured["messages"][0]["role"] == "system"
    assert captured["messages"][1]["role"] == "user"


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_invalid_json():
    with pytest.raises(OutlineGenerationError, match="valid JSON"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            llm=FakeLLM("not json"),
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("raw_response", ["", "   ", "```json\n\n```"])
async def test_generate_outline_options_rejects_empty_llm_response(raw_response: str):
    with pytest.raises(OutlineGenerationError, match="empty response"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            llm=FakeLLM(raw_response),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_non_string_llm_response():
    with pytest.raises(OutlineGenerationError, match="content must be a string"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            llm=FakeLLM({"not": "text"}),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_missing_required_field():
    payload = _valid_payload()
    del payload["options"][0]["chapterGoal"]

    with pytest.raises(OutlineGenerationError, match="chapterGoal"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_repairs_empty_characters_involved_from_scenes():
    payload = _valid_payload()
    for option in payload["options"]:
        option["charactersInvolved"] = []

    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
        llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
    )

    assert result.options[0].characters_involved[0].name == "Lin Jin"
    assert result.options[1].characters_involved[0].motivation
    assert result.options[2].characters_involved[0].state_change is not None


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_missing_option_code():
    payload = _valid_payload()
    payload["options"][2] = _valid_option("B", "conflict")

    with pytest.raises(OutlineGenerationError, match="A, B, and C"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_builds_context_and_llm_messages():
    fake_llm = FakeLLM(json.dumps(_valid_payload(), ensure_ascii=False))

    await generate_outline_options(
        story={"id": "story-1", "title": "Dream Fire"},
        chapter={"id": "chapter-2", "chapterNumber": 2, "goal": "Find the hidden token"},
        option_group_id="group-1",
        blueprint={"id": "bp-1", "premise": "A betrayed disciple uses dream visions."},
        recent_chapters=[{"id": "chapter-1", "summary": "Lin Jin escaped the sect."}],
        timeline=[{"id": "tl-1", "summary": "The sect framed Lin Jin."}],
        characters={"lin-jin": {"name": "Lin Jin", "state": "injured"}},
        world={"rules": {"dream-fire": "Dream fire cannot show complete futures."}},
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
        additional_memory={"lockedFacts": ["Dream visions are fragmented."]},
        llm=fake_llm,
    )

    assert fake_llm.messages is not None
    assert len(fake_llm.messages) == 2
    human_message = fake_llm.messages[1]["content"]
    assert '"storyId": "story-1"' in human_message
    assert '"chapterId": "chapter-2"' in human_message
    assert '"optionGroupId": "group-1"' in human_message
    assert "Dream visions are fragmented." in human_message
    assert "fs-1" in human_message


@pytest.mark.asyncio
async def test_generate_outline_options_accepts_prebuilt_context():
    fake_llm = FakeLLM(json.dumps(_valid_payload(), ensure_ascii=False))
    context = OutlineOptionsPromptContext(
        story_id="story-1",
        chapter_id="chapter-2",
        option_group_id="group-1",
        blueprint={"premise": "A betrayed disciple uses dream visions."},
        existing_foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
    )

    await generate_outline_options(context=context, llm=fake_llm)

    assert fake_llm.messages is not None
    assert "A betrayed disciple uses dream visions." in fake_llm.messages[1]["content"]


@pytest.mark.asyncio
@pytest.mark.parametrize("action", ["resolve", "trigger"])
async def test_generate_outline_options_allows_c_to_resolve_or_trigger_existing_foreshadow(
    action: str,
):
    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
        llm=FakeLLM(json.dumps(_payload_with_c_action(action), ensure_ascii=False)),
    )

    assert result.options[2].foreshadow_actions[0].action == action


@pytest.mark.asyncio
async def test_generate_outline_options_allows_c_to_strengthen_existing_foreshadow():
    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
        llm=FakeLLM(json.dumps(_payload_with_c_action("strengthen"), ensure_ascii=False)),
    )

    assert result.options[2].foreshadow_actions[0].action == "strengthen"


@pytest.mark.asyncio
async def test_generate_outline_options_allows_c_plant_when_existing_foreshadows_under_budget():
    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
        llm=FakeLLM(json.dumps(_payload_with_c_action("plant", None), ensure_ascii=False)),
    )

    assert result.options[2].foreshadow_actions[0].action == "plant"


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_c_plant_when_active_foreshadow_budget_is_full():
    with pytest.raises(OutlineGenerationError, match="budget is full"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=_existing_foreshadows(10),
            llm=FakeLLM(
                json.dumps(_payload_with_c_action("plant", None), ensure_ascii=False)
            ),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_c_plant_when_urgent_foreshadow_is_unhandled():
    with pytest.raises(OutlineGenerationError, match="urgent existing foreshadow"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=[
                {
                    "id": "fs-1",
                    "summary": "The token clue is overdue.",
                    "needsAttention": True,
                }
            ],
            llm=FakeLLM(json.dumps(_payload_with_c_action("plant", None), ensure_ascii=False)),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_allows_c_to_handle_urgent_foreshadow_and_plant():
    payload = _valid_payload()
    payload["options"][2]["foreshadowActions"] = [
        {
            "action": "strengthen",
            "description": "Bring the overdue token clue back into the scene.",
            "foreshadowId": "fs-1",
        },
        {
            "action": "plant",
            "description": "Plant a light new clue for the next arc.",
            "foreshadowId": None,
        },
    ]

    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        foreshadows=[
            {
                "id": "fs-1",
                "summary": "The token clue is overdue.",
                "attentionStatus": "overdue",
            }
        ],
        llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
    )

    assert [action.action for action in result.options[2].foreshadow_actions] == [
        "strengthen",
        "plant",
    ]


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_c_plant_with_existing_without_risk_notes():
    payload = _payload_with_c_action("plant", None)
    payload["options"][2]["riskNotes"] = []

    with pytest.raises(OutlineGenerationError, match="riskNotes"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
            llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_c_unknown_foreshadow_id():
    with pytest.raises(OutlineGenerationError, match="unknown foreshadowId"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
            llm=FakeLLM(
                json.dumps(_payload_with_c_action("trigger", "fs-missing"), ensure_ascii=False)
            ),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_c_existing_action_without_id():
    with pytest.raises(OutlineGenerationError, match="must include foreshadowId"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
            llm=FakeLLM(
                json.dumps(_payload_with_c_action("trigger", None), ensure_ascii=False)
            ),
        )


@pytest.mark.asyncio
async def test_generate_outline_options_allows_c_plant_without_existing_foreshadows():
    result = await generate_outline_options(
        story_id="story-1",
        chapter_id="chapter-2",
        llm=FakeLLM(json.dumps(_payload_with_c_action("plant", None), ensure_ascii=False)),
    )

    assert result.options[2].foreshadow_actions[0].action == "plant"


@pytest.mark.asyncio
async def test_generate_outline_options_rejects_c_without_foreshadow_actions():
    payload = _valid_payload()
    payload["options"][2]["foreshadowActions"] = []

    with pytest.raises(OutlineGenerationError, match="at least one foreshadow action"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
            llm=FakeLLM(json.dumps(payload, ensure_ascii=False)),
        )
