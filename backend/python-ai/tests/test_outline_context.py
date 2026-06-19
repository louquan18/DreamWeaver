import pytest

from src.memory.schema import CharacterState, Foreshadow, TimelineEvent, WorldState
from src.schemas.blueprint import NovelBlueprintDraft
from src.services.outline_context import build_outline_options_context
from src.services.outline_prompt import OutlineOptionsPromptContext


def test_outline_context_adapts_blueprint_and_preserves_ids():
    blueprint = NovelBlueprintDraft.model_validate(
        {
            "storyId": "story-1",
            "sourcePrompt": "A betrayed cultivator follows prophetic dreams.",
            "premise": "Betrayed cultivator seeks the truth behind dream fire.",
            "genre": "xianxia",
            "tone": "suspense",
            "protagonist": {"name": "Lin Jin", "initialGoal": "survive"},
            "mainThread": {"goal": "uncover the sect conspiracy"},
            "coreConflict": {"external": "sect pursuit", "stakes": "memory erasure"},
            "worldSeed": {"rules": ["Dream fire only reveals fragments"]},
            "writingPreferences": {"targetWords": 300000},
            "lockedFacts": [{"id": "fact-1", "text": "Dreams are fragmentary"}],
            "status": "confirmed",
        }
    )

    context = build_outline_options_context(
        chapter={"id": "chapter-2", "number": 2},
        blueprint=blueprint,
    )

    assert isinstance(context, OutlineOptionsPromptContext)
    assert context.story_id == "story-1"
    assert context.chapter_id == "chapter-2"
    assert context.blueprint["storyId"] == "story-1"
    assert context.blueprint["lockedFacts"][0]["id"] == "fact-1"
    assert context.blueprint["mainThread"]["goal"] == "uncover the sect conspiracy"


def test_outline_context_adapts_main_thread_and_author_intent():
    context = build_outline_options_context(
        story_id="story-1",
        chapter={
            "chapterId": "chapter-3",
            "chapterNumber": "3",
            "title": "Dream Fire Gate",
            "goal": "force the protagonist to choose between escape and rescue",
            "summary": "",
        },
        blueprint={"mainThread": {"goal": "expose the hidden master"}},
        author_intent={"focus": "raise moral pressure", "avoid": ""},
    )

    assert context.chapter_number == 3
    assert context.chapter_intent == {
        "chapterId": "chapter-3",
        "chapterNumber": 3,
        "title": "Dream Fire Gate",
        "goal": "force the protagonist to choose between escape and rescue",
        "mainThread": {"goal": "expose the hidden master"},
        "authorIntent": {"focus": "raise moral pressure"},
    }


def test_outline_context_adapts_recent_chapters_and_filters_empty_items():
    context = build_outline_options_context(
        story_id="story-1",
        chapter_id="chapter-4",
        recent_chapters=[
            {
                "id": "chapter-1",
                "number": 1,
                "title": "Outer Gate Escape",
                "summary": "Lin Jin escaped the outer gate.",
                "status": "CONFIRMED",
                "unused": "",
            },
            {"id": "", "summary": "  "},
            None,
        ],
    )

    assert context.recent_chapters == [
        {
            "chapterId": "chapter-1",
            "chapterNumber": 1,
            "title": "Outer Gate Escape",
            "summary": "Lin Jin escaped the outer gate.",
            "status": "CONFIRMED",
        }
    ]


def test_outline_context_adapts_timeline_character_and_world_memory():
    character = CharacterState(name="Lin Jin")
    character.current_state.location = "Forbidden valley"
    character.current_state.health_status = "wounded"

    world = WorldState(
        rules={"dream_fire": "Only predicts fragments"},
        locations={"forbidden_valley": {"danger": "ancient seal"}},
    )

    context = build_outline_options_context(
        story_id="story-1",
        chapter_id="chapter-5",
        timeline=[
            TimelineEvent(chapter=1, event="Lin Jin was expelled.", importance="high"),
            {"id": "tl-2", "summary": ""},
        ],
        characters={"lin-jin": character},
        world=world,
    )

    assert context.timeline_memory == [
        {
            "chapter": 1,
            "event": "Lin Jin was expelled.",
            "importance": "high",
            "is_permanent": False,
        },
        {"id": "tl-2"},
    ]
    assert context.character_memory[0]["name"] == "Lin Jin"
    assert context.character_memory[0]["current_state"]["location"] == "Forbidden valley"
    assert {"type": "rule", "name": "dream_fire", "details": "Only predicts fragments"} in (
        context.world_memory
    )
    assert {
        "type": "location",
        "name": "forbidden_valley",
        "details": {"danger": "ancient seal"},
    } in context.world_memory


def test_outline_context_preserves_mapping_keys_as_memory_ids():
    context = build_outline_options_context(
        story_id="story-1",
        chapter_id="chapter-5",
        timeline={
            "tl-1": {"summary": "The protagonist saw the first dream fire fragment."},
        },
    )

    assert context.timeline_memory == [
        {
            "id": "tl-1",
            "summary": "The protagonist saw the first dream fire fragment.",
        }
    ]


def test_outline_context_adapts_open_foreshadows_and_drops_terminal_statuses():
    context = build_outline_options_context(
        story_id="story-1",
        chapter_id="chapter-6",
        foreshadows=[
            Foreshadow(
                id="fs-1",
                chapter_planted=2,
                content="The token carries dream fire marks.",
                status="planted",
                planned_payoff_hint="connect it to the forbidden valley",
            ),
            {"id": "fs-2", "content": "already solved", "status": "resolved"},
            {"foreshadowId": "fs-3", "summary": "blank status stays available"},
            {"content": "no id should not be recoverable", "status": "planted"},
        ],
    )

    assert context.existing_foreshadows == [
        {
            "id": "fs-1",
            "summary": "The token carries dream fire marks.",
            "content": "The token carries dream fire marks.",
            "status": "planted",
            "importance": "medium",
            "chapterPlanted": 2,
            "plannedPayoffHint": "connect it to the forbidden valley",
            "attentionStatus": "normal",
            "needsAttention": False,
        },
        {"id": "fs-3", "summary": "blank status stays available"},
    ]


def test_outline_context_drops_blank_id_and_terminal_foreshadow_combinations():
    context = build_outline_options_context(
        story_id="story-1",
        chapter_id="chapter-6",
        foreshadows=[
            {"id": " ", "content": "blank id cannot be recovered", "status": "planted"},
            {"id": "fs-resolved", "content": "resolved clue", "status": "resolved"},
            {"id": "fs-abandoned", "content": "abandoned clue", "status": "abandoned"},
            {"foreshadowId": "fs-open", "summary": "open clue", "status": "triggered"},
        ],
    )

    assert context.existing_foreshadows == [
        {"id": "fs-open", "summary": "open clue", "status": "triggered"}
    ]


def test_outline_context_empty_optional_inputs_are_safe():
    context = build_outline_options_context(story_id="story-1", chapter_id="chapter-1")

    assert context.blueprint == {}
    assert context.chapter_intent == {}
    assert context.recent_chapters == []
    assert context.timeline_memory == []
    assert context.character_memory == []
    assert context.world_memory == []
    assert context.existing_foreshadows == []
    assert context.additional_memory == {}


def test_outline_context_requires_real_story_and_chapter_ids():
    with pytest.raises(ValueError, match="story_id is required"):
        build_outline_options_context(chapter_id="chapter-1")

    with pytest.raises(ValueError, match="chapter_id is required"):
        build_outline_options_context(story_id="story-1")
