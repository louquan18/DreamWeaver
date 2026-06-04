"""NovelState - 小说创作工作流状态定义"""

from typing import Any, Optional

from typing_extensions import TypedDict


class NovelState(TypedDict, total=False):
    """
    小说创作工作流状态

    使用 TypedDict 定义状态结构，LangGraph 自动管理状态传递和合并。
    total=False 表示所有字段可选（允许 partial update）。
    """

    # ========== 基础信息 ==========
    story_id: str
    chapter_id: str
    user_id: str

    # ========== 上下文信息 ==========
    novel_context: dict[str, Any]
    """小说上下文 (recent_chapters, characters, timeline, world_state, foreshadows)"""

    chapter_outline: dict[str, Any]
    """章节大纲 (goal, conflict, plot_points, estimated_words)"""

    # ========== 生成内容 ==========
    generated_draft: str

    # ========== 检查报告 ==========
    consistency_report: dict[str, Any]
    """一致性报告 (character_issues, world_issues, plot_issues, total_issues)"""

    review_report: dict[str, Any]
    """评审报告 (score, language_quality, rhythm_control, suggestions)"""

    # ========== 执行状态 ==========
    execution_history: list[str]
    current_node: Optional[str]

    # ========== 错误处理 ==========
    error: Optional[str]
    retry_count: int

    # ========== 元数据 ==========
    metadata: dict[str, Any]


def create_initial_state(
    story_id: str,
    chapter_id: str,
    user_id: str = "",
) -> NovelState:
    """创建工作流初始状态"""
    return NovelState(
        story_id=story_id,
        chapter_id=chapter_id,
        user_id=user_id,
        novel_context={},
        chapter_outline={},
        generated_draft="",
        consistency_report={},
        review_report={},
        execution_history=[],
        current_node=None,
        error=None,
        retry_count=0,
        metadata={},
    )
