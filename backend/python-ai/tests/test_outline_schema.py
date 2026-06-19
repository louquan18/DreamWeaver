import pytest
from pydantic import ValidationError

from src.schemas.outline import (
    CHAPTER_OUTLINE_CONTENT_JSON_SCHEMA,
    ChapterOutlineDraft,
    ChapterOutlineOptionDraft,
    ChapterOutlineOptionsDraft,
)


def valid_outline_content():
    return {
        "title_candidates": ["梦火初燃", "禁地回声"],
        "chapter_goal": "让主角发现梦境预知与宗门禁地有关",
        "story_summary": "主角被迫进入禁地，在追杀中看见未来片段，并决定反查宗门背叛。",
        "scene_outline": [
            {
                "order": 1,
                "summary": "主角躲入废弃丹房",
                "purpose": "承接上一章追杀压力",
                "characters": ["林烬"],
                "location": "外门丹房",
                "outcome": "发现禁地令牌",
            },
            {
                "order": 2,
                "summary": "追兵逼近，梦境碎片提前出现",
                "purpose": "展示能力限制",
                "characters": ["林烬", "执法弟子"],
                "location": "禁地石阶",
                "outcome": "主角避开第一轮搜捕",
            },
            {
                "order": 3,
                "summary": "主角看见师尊与黑影交易",
                "purpose": "推进背叛主线",
                "characters": ["林烬", "玄衣人"],
                "location": "禁地门前",
                "outcome": "主角确认宗门内部有更深阴谋",
            },
        ],
        "characters_involved": [
            {
                "name": "林烬",
                "role": "主角",
                "motivation": "活下去并确认背叛真相",
                "state_change": "从逃亡转为主动调查",
            }
        ],
        "conflict": {
            "external": "执法堂追杀",
            "internal": "是否继续相信旧日师门",
            "stakes": "失败会被废去灵根并抹除记忆",
        },
        "highlight_moment": "主角用梦境碎片反制追兵",
        "foreshadow_actions": [
            {
                "action": "plant",
                "description": "禁地令牌背面出现与主角梦境相同的火纹",
                "foreshadow_id": "fs-001",
            }
        ],
        "memory_references": [
            {
                "type": "blueprint",
                "summary": "梦境只能看到碎片，不能完整预知未来",
                "relevance": "限制主角能力，避免无代价开挂",
            }
        ],
        "why_this_plan": "先用追杀建立紧迫感，再用禁地线索推进主线。",
        "ending_hook": "黑影说出主角母亲的旧名。",
        "risk_notes": ["不要过早暴露黑影真实身份"],
    }


def test_outline_option_accepts_standard_fields_and_java_metadata_aliases():
    payload = {
        **valid_outline_content(),
        "storyId": "story-1",
        "chapterId": "chapter-1",
        "optionGroupId": "group-1",
        "optionCode": "A",
        "optionType": "steady",
    }

    option = ChapterOutlineOptionDraft.model_validate(payload)

    assert option.option_code == "A"
    assert option.option_type == "steady"
    assert option.scene_outline[0].summary == "主角躲入废弃丹房"
    assert option.model_dump(by_alias=True)["optionCode"] == "A"


def test_outline_content_requires_three_to_five_scenes():
    payload = {
        **valid_outline_content(),
        "story_id": "story-1",
        "chapter_id": "chapter-1",
        "option_code": "B",
        "option_type": "conflict",
    }
    payload["scene_outline"] = payload["scene_outline"][:2]

    with pytest.raises(ValidationError):
        ChapterOutlineOptionDraft.model_validate(payload)


def test_outline_options_must_cover_a_b_c_and_three_types():
    base = valid_outline_content()
    options = []
    for code, option_type in (("A", "steady"), ("B", "conflict"), ("C", "foreshadow")):
        options.append(
            {
                **base,
                "story_id": "story-1",
                "chapter_id": "chapter-1",
                "option_code": code,
                "option_type": option_type,
            }
        )

    draft = ChapterOutlineOptionsDraft.model_validate(
        {"story_id": "story-1", "chapter_id": "chapter-1", "options": options}
    )

    assert [option.option_code for option in draft.options] == ["A", "B", "C"]


def test_confirmed_outline_wraps_standard_final_outline():
    outline = ChapterOutlineDraft.model_validate(
        {
            "story_id": "story-1",
            "chapter_id": "chapter-1",
            "source_option_ids": ["option-a", "option-c"],
            "user_feedback": "保留 C 的章末钩子",
            "final_outline": valid_outline_content(),
            "status": "confirmed",
        }
    )

    assert outline.final_outline.ending_hook == "黑影说出主角母亲的旧名。"
    assert outline.model_dump(by_alias=True)["finalOutline"]["chapterGoal"].startswith("让主角")


def test_exported_json_schema_contains_p3_t1_standard_fields():
    assert set(ChapterOutlineDraft.model_fields["final_outline"].annotation.model_fields) >= {
        "title_candidates",
        "chapter_goal",
        "story_summary",
        "scene_outline",
        "characters_involved",
        "conflict",
        "highlight_moment",
        "foreshadow_actions",
        "memory_references",
        "why_this_plan",
        "ending_hook",
        "risk_notes",
    }

    properties = CHAPTER_OUTLINE_CONTENT_JSON_SCHEMA["properties"]

    assert set(properties) >= {
        "titleCandidates",
        "chapterGoal",
        "storySummary",
        "sceneOutline",
        "charactersInvolved",
        "conflict",
        "highlightMoment",
        "foreshadowActions",
        "memoryReferences",
        "whyThisPlan",
        "endingHook",
        "riskNotes",
    }
    assert properties["sceneOutline"]["minItems"] == 3
    assert properties["sceneOutline"]["maxItems"] == 5
