import json

from langchain_core.messages import HumanMessage, SystemMessage

from src.services.outline_prompt import (
    OutlineOptionsPromptContext,
    build_outline_options_prompt,
)


def test_outline_options_prompt_builds_system_and_human_messages():
    context = OutlineOptionsPromptContext(
        story_id="story-1",
        chapter_id="chapter-2",
        option_group_id="group-1",
        chapter_number=2,
        blueprint={"premise": "被宗门背叛的少年靠梦境预知复仇"},
        chapter_intent={"goal": "查清宗门背后的黑影"},
        recent_chapters=[{"chapterId": "chapter-1", "summary": "主角逃出外门丹房"}],
        timeline_memory=[{"id": "tl-001", "summary": "主角被逐出宗门"}],
        character_memory=[{"id": "char-001", "name": "林烬", "state": "受伤但清醒"}],
        world_memory=[{"id": "world-001", "summary": "梦火纹与禁地令牌有关"}],
        existing_foreshadows=[
            {
                "id": "fs-001",
                "summary": "禁地令牌背面有梦火纹",
                "status": "planned",
            }
        ],
        additional_memory={"lockedFacts": ["黑影身份暂不揭露"]},
    )

    messages = build_outline_options_prompt(context)

    assert len(messages) == 2
    assert isinstance(messages[0], SystemMessage)
    assert isinstance(messages[1], HumanMessage)
    assert '"storyId": "story-1"' in messages[1].content
    assert '"chapterId": "chapter-2"' in messages[1].content
    assert '"id": "fs-001"' in messages[1].content
    assert "黑影身份暂不揭露" in messages[1].content


def test_outline_options_prompt_requires_chapter_outline_options_schema():
    system_prompt = build_outline_options_prompt(
        OutlineOptionsPromptContext(story_id="story-1", chapter_id="chapter-1")
    )[0].content

    assert "ChapterOutlineOptionsDraft schema" in system_prompt
    assert "只输出一个 JSON object" in system_prompt
    assert "不输出 Markdown、代码块、解释或额外文本" in system_prompt
    assert '"options"' in system_prompt
    assert '"titleCandidates"' in system_prompt
    assert '"sceneOutline"' in system_prompt
    assert '"whyThisPlan"' in system_prompt
    assert '"foreshadowActions"' in system_prompt


def test_outline_options_prompt_pins_a_b_c_option_codes_and_types():
    messages = build_outline_options_prompt(
        OutlineOptionsPromptContext(story_id="story-1", chapter_id="chapter-1")
    )
    system_prompt = messages[0].content
    human_payload = _extract_json_block(messages[1].content, "固定元数据：", "小说蓝图：")

    assert 'optionCode="A" 且 optionType="steady"' in system_prompt
    assert 'optionCode="B" 且 optionType="conflict"' in system_prompt
    assert 'optionCode="C" 且 optionType="foreshadow"' in system_prompt
    assert human_payload["requiredOptions"] == [
        {"optionCode": "A", "optionType": "steady"},
        {"optionCode": "B", "optionType": "conflict"},
        {"optionCode": "C", "optionType": "foreshadow"},
    ]


def test_outline_options_prompt_documents_c_foreshadow_fallback_rules():
    system_prompt = build_outline_options_prompt(
        OutlineOptionsPromptContext(story_id="story-1", chapter_id="chapter-1")
    )[0].content

    assert "C 方案伏笔兜底规则" in system_prompt
    assert "优先回收已有伏笔" in system_prompt
    assert 'action="resolve"' in system_prompt
    assert 'action="trigger"' in system_prompt
    assert "其次强化已有伏笔" in system_prompt
    assert 'action="strengthen"' in system_prompt
    assert "最后才埋设新伏笔" in system_prompt
    assert 'action="plant"' in system_prompt
    assert "禁止伪造不存在的前文伏笔" in system_prompt
    assert "没有输入 foreshadowId 时，不能声称其来自历史章节" in system_prompt


def test_outline_options_prompt_has_context_slots_for_future_context_loader():
    human_prompt = build_outline_options_prompt(
        OutlineOptionsPromptContext(
            story_id="story-1",
            chapter_id="chapter-1",
            timeline_memory=[{"id": "tl-001"}],
            character_memory=[{"id": "char-001"}],
            world_memory=[{"id": "world-001"}],
        )
    )[1].content

    assert "近期历史章节" in human_prompt
    assert "时间线记忆" in human_prompt
    assert "人物记忆" in human_prompt
    assert "世界观记忆" in human_prompt
    assert "已有伏笔 existingForeshadows" in human_prompt
    assert '"id": "tl-001"' in human_prompt
    assert '"id": "char-001"' in human_prompt
    assert '"id": "world-001"' in human_prompt


def _extract_json_block(content: str, start_label: str, end_label: str) -> dict:
    start = content.index(start_label) + len(start_label)
    end = content.index(end_label)
    return json.loads(content[start:end].strip())
