import json
from types import SimpleNamespace

import pytest

from src.services.outline_prompt import OutlineOptionsPromptContext
from src.services.outline_service import OutlineGenerationError, generate_outline_options


class FakeLLM:
    def __init__(self, content: str):
        self.content = content
        self.messages = None

    async def ainvoke(self, messages):
        self.messages = messages
        return SimpleNamespace(content=self.content)


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
async def test_generate_outline_options_rejects_invalid_json():
    with pytest.raises(OutlineGenerationError, match="valid JSON"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            llm=FakeLLM("not json"),
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
    human_message = fake_llm.messages[1].content
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
    assert "A betrayed disciple uses dream visions." in fake_llm.messages[1].content


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
async def test_generate_outline_options_rejects_c_plant_when_existing_foreshadow_available():
    with pytest.raises(OutlineGenerationError, match="cannot plant"):
        await generate_outline_options(
            story_id="story-1",
            chapter_id="chapter-2",
            foreshadows=[{"id": "fs-1", "summary": "The token carries a dream-fire mark."}],
            llm=FakeLLM(
                json.dumps(_payload_with_c_action("plant", None), ensure_ascii=False)
            ),
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
