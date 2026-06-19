"""Prompt builder for P3 A/B/C chapter outline options."""

# ruff: noqa: E501

import json
from dataclasses import dataclass, field
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from src.schemas.outline import ChapterOutlineOptionsDraft

OUTLINE_OPTIONS_SYSTEM_PROMPT = """你是 DreamWeaver 的章节中纲策划 Agent。你的任务是为同一章生成 A/B/C 三个可供作者选择的中纲方案。

输出规则：
- 只输出一个 JSON object，不输出 Markdown、代码块、解释或额外文本。
- JSON 必须严格符合 ChapterOutlineOptionsDraft schema，字段使用 schema 中的 camelCase 名称。
- 顶层必须包含 storyId、chapterId、optionGroupId、options。
- options 必须且只能有 3 项，按 A、B、C 顺序排列。
- A 方案必须是 optionCode="A" 且 optionType="steady"，用于稳健推进。
- B 方案必须是 optionCode="B" 且 optionType="conflict"，用于强冲突。
- C 方案必须是 optionCode="C" 且 optionType="foreshadow"，用于伏笔回收。
- 每个方案都必须有 3-5 个 sceneOutline 场景，并写清 whyThisPlan，解释为什么这样写。
- 每个方案都必须引用输入上下文中已经存在的蓝图、历史章节、时间线、人物、世界观或伏笔信息作为 memoryReferences。
- memoryReferences 只能引用输入上下文中真实存在的信息，不得凭空创造历史章节、记忆条目或前文伏笔。
- 不要改写已锁定设定，不要让角色突然获得未铺垫能力，不要提前确认作者尚未确认的新世界观。

A/B/C 方案差异：
- A steady：承接上一章和主线目标，优先保持节奏稳定、信息清晰、人物状态自然推进。
- B conflict：在不违背已知设定的前提下，提高外部或内部冲突强度，让本章有明确对抗、代价和选择压力。
- C foreshadow：优先围绕伏笔推进，必须执行伏笔兜底规则。

C 方案伏笔兜底规则：
1. 优先回收已有伏笔：如果输入的 existingForeshadows 中存在适合本章解决或触发的伏笔，使用 action="resolve" 或 action="trigger"，并在 foreshadowId 中引用原 id。
2. 其次强化已有伏笔：如果暂不适合回收，但已有伏笔可以加深读者期待，使用 action="strengthen"，并引用原 foreshadowId。
3. 最后才埋设新伏笔：只有在 existingForeshadows 为空，或全部明确不适合本章处理时，才允许使用 action="plant"。
4. 禁止伪造不存在的前文伏笔：不得把本章新写的线索描述成“前文已经出现”；没有输入 foreshadowId 时，不能声称其来自历史章节。
5. 当 C 方案埋设新伏笔时，riskNotes 必须说明为什么没有回收或强化已有伏笔。

ChapterOutlineOptionsDraft schema：
{schema}
"""

OUTLINE_OPTIONS_HUMAN_PROMPT = """请基于以下上下文，为目标章节生成 A/B/C 三个章节中纲方案。

固定元数据：
{metadata}

小说蓝图：
{blueprint}

章节目标与作者意图：
{chapter_intent}

近期历史章节：
{recent_chapters}

时间线记忆：
{timeline_memory}

人物记忆：
{character_memory}

世界观记忆：
{world_memory}

已有伏笔 existingForeshadows：
{existing_foreshadows}

其他结构化记忆：
{additional_memory}

请严格返回 ChapterOutlineOptionsDraft JSON。"""


@dataclass(frozen=True)
class OutlineOptionsPromptContext:
    """Inputs needed to build a chapter outline options prompt."""

    story_id: str
    chapter_id: str
    option_group_id: str | None = None
    chapter_number: int | None = None
    blueprint: dict[str, Any] = field(default_factory=dict)
    chapter_intent: dict[str, Any] = field(default_factory=dict)
    recent_chapters: list[dict[str, Any]] = field(default_factory=list)
    timeline_memory: list[dict[str, Any]] = field(default_factory=list)
    character_memory: list[dict[str, Any]] = field(default_factory=list)
    world_memory: list[dict[str, Any]] = field(default_factory=list)
    existing_foreshadows: list[dict[str, Any]] = field(default_factory=list)
    additional_memory: dict[str, Any] = field(default_factory=dict)


def build_outline_options_prompt(
    context: OutlineOptionsPromptContext,
) -> list[SystemMessage | HumanMessage]:
    """Build messages for generating P3 A/B/C chapter outline options."""
    metadata = {
        "storyId": context.story_id,
        "chapterId": context.chapter_id,
        "optionGroupId": context.option_group_id,
        "chapterNumber": context.chapter_number,
        "requiredOptions": [
            {"optionCode": "A", "optionType": "steady"},
            {"optionCode": "B", "optionType": "conflict"},
            {"optionCode": "C", "optionType": "foreshadow"},
        ],
    }

    return [
        SystemMessage(content=OUTLINE_OPTIONS_SYSTEM_PROMPT.format(schema=_json(_schema()))),
        HumanMessage(
            content=OUTLINE_OPTIONS_HUMAN_PROMPT.format(
                metadata=_json(metadata),
                blueprint=_json(context.blueprint),
                chapter_intent=_json(context.chapter_intent),
                recent_chapters=_json(context.recent_chapters),
                timeline_memory=_json(context.timeline_memory),
                character_memory=_json(context.character_memory),
                world_memory=_json(context.world_memory),
                existing_foreshadows=_json(context.existing_foreshadows),
                additional_memory=_json(context.additional_memory),
            )
        ),
    ]


def _schema() -> dict[str, Any]:
    return ChapterOutlineOptionsDraft.model_json_schema(by_alias=True)


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
