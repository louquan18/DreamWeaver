import pytest
from pydantic import ValidationError

from src.schemas.blueprint import LightBlueprintGenerateRequest, NovelBlueprintDraft


def test_generate_request_accepts_java_style_aliases():
    request = LightBlueprintGenerateRequest.model_validate(
        {
            "sourcePrompt": "一个被宗门背叛的少年靠梦境预知复仇",
            "genre": "xianxia",
            "tone": "热血爽文",
            "targetWords": 300000,
        }
    )

    assert request.source_prompt.startswith("一个被宗门背叛")
    assert request.target_words == 300000


def test_generate_request_rejects_blank_prompt():
    with pytest.raises(ValidationError):
        LightBlueprintGenerateRequest.model_validate({"sourcePrompt": "   "})


def test_blueprint_draft_requires_locked_fact_text():
    with pytest.raises(ValidationError):
        NovelBlueprintDraft.model_validate(
            {
                "story_id": "story-1",
                "source_prompt": "idea",
                "premise": "premise",
                "protagonist": {"name": "林烬"},
                "main_thread": {"goal": "复仇"},
                "core_conflict": {"external": "追杀"},
                "world_seed": {"rules": []},
                "writing_preferences": {"pace": "fast"},
                "locked_facts": [{"category": "world"}],
            }
        )


def test_blueprint_draft_serializes_java_style_aliases():
    blueprint = NovelBlueprintDraft.model_validate(
        {
            "story_id": "story-1",
            "source_prompt": "idea",
            "premise": "premise",
            "protagonist": {"name": "林烬"},
            "main_thread": {"goal": "复仇"},
            "core_conflict": {"external": "追杀"},
            "world_seed": {"rules": []},
            "writing_preferences": {"pace": "fast"},
            "locked_facts": [{"text": "梦境只能看到碎片"}],
        }
    )

    data = blueprint.model_dump(by_alias=True)
    assert data["storyId"] == "story-1"
    assert data["sourcePrompt"] == "idea"
    assert data["mainThread"]["goal"] == "复仇"
    assert data["lockedFacts"][0]["text"] == "梦境只能看到碎片"
