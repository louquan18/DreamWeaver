"""LangGraph StateGraph 工作流定义

核心工作流：
  load_runtime_context → novel_context → plan_chapter → generate_draft
  → check_consistency → [review ↔ rewrite] → commit → END
"""

from typing import Any, Literal

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from loguru import logger

from .state import NovelState
from .nodes import (
    commit_node,
    consistency_agent_node,
    context_agent_node,
    load_runtime_context_node,
    planner_agent_node,
    reviewer_agent_node,
    rewrite_agent_node,
    writer_agent_node,
)


# ========== 条件路由函数 ==========


def should_continue_to_review(
    state: dict[str, Any],
) -> Literal["review", "commit"]:
    """
    一致性检查后决定下一步

    - 有 high 级别问题 → 必须 review
    - 有 3+ 个问题 → review
    - 否则 → commit
    """
    report = state.get("consistency_report", {})
    total_issues = report.get("total_issues", 0)
    high_issues = report.get("high_issues", 0)

    if high_issues > 0:
        logger.info(f"[Router] {high_issues} high-severity issues → review")
        return "review"

    if total_issues >= 3:
        logger.info(f"[Router] {total_issues} issues (>=3) → review")
        return "review"

    if total_issues > 0:
        logger.info(f"[Router] {total_issues} minor issues → commit (acceptable)")
        return "commit"

    logger.info("[Router] No issues → commit")
    return "commit"


def should_rewrite(
    state: dict[str, Any],
) -> Literal["rewrite", "commit"]:
    """
    评审后决定是否需要重写

    - 评分 < 75 且重试次数 < 3 → rewrite
    - 否则 → commit
    """
    report = state.get("review_report", {})
    score = report.get("score", 0)
    retry_count = state.get("retry_count", 0)

    if score < 75 and retry_count < 3:
        logger.info(f"[Router] Score {score} < 75, retry {retry_count + 1}/3 → rewrite")
        return "rewrite"

    logger.info(f"[Router] Score {score} >= 75 or max retries → commit")
    return "commit"


# ========== 构建工作流 ==========


def create_novel_workflow(checkpointer=None) -> Any:
    """
    创建小说创作工作流

    Args:
        checkpointer: Checkpoint 存储后端，默认 MemorySaver

    Returns:
        编译后的 LangGraph 应用
    """
    if checkpointer is None:
        checkpointer = MemorySaver()

    workflow = StateGraph(NovelState)

    # 添加节点
    workflow.add_node("load_runtime_context", load_runtime_context_node)
    workflow.add_node("novel_context", context_agent_node)
    workflow.add_node("plan_chapter", planner_agent_node)
    workflow.add_node("generate_draft", writer_agent_node)
    workflow.add_node("check_consistency", consistency_agent_node)
    workflow.add_node("review", reviewer_agent_node)
    workflow.add_node("rewrite", rewrite_agent_node)
    workflow.add_node("commit", commit_node)

    # 设置入口点
    workflow.set_entry_point("load_runtime_context")

    # 顺序边
    workflow.add_edge("load_runtime_context", "novel_context")
    workflow.add_edge("novel_context", "plan_chapter")
    workflow.add_edge("plan_chapter", "generate_draft")
    workflow.add_edge("generate_draft", "check_consistency")

    # 条件边：一致性检查后
    workflow.add_conditional_edges(
        "check_consistency",
        should_continue_to_review,
        {
            "review": "review",
            "commit": "commit",
        },
    )

    # 条件边：评审后
    workflow.add_conditional_edges(
        "review",
        should_rewrite,
        {
            "rewrite": "rewrite",
            "commit": "commit",
        },
    )

    # 重写后返回评审（循环）
    workflow.add_edge("rewrite", "review")

    # 提交后结束
    workflow.add_edge("commit", END)

    app = workflow.compile(checkpointer=checkpointer)
    logger.info("[Graph] Novel workflow compiled successfully")
    return app


# 默认工作流实例（MemorySaver，开发用）
default_app = create_novel_workflow()
