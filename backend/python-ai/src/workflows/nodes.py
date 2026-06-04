"""工作流节点封装

将 Agent 节点包装为 LangGraph 兼容的函数，
并添加 commit 等辅助节点。
"""

from typing import Any

from loguru import logger

from src.agents import (
    consistency_agent_node,
    context_agent_node,
    planner_agent_node,
    reviewer_agent_node,
    rewrite_agent_node,
    writer_agent_node,
)


async def load_runtime_context_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    加载运行时上下文节点

    职责：
    - 验证输入参数完整性
    - 初始化元数据
    """
    logger.info(f"[Runtime] Loading context for story={state.get('story_id')}")

    return {
        "current_node": "load_runtime_context",
        "execution_history": state.get("execution_history", []) + ["load_runtime_context"],
        "metadata": {
            **state.get("metadata", {}),
            "initialized": True,
        },
    }


async def commit_node(state: dict[str, Any]) -> dict[str, Any]:
    """
    提交节点 - 工作流最终步骤

    职责：
    - 标记工作流完成
    - 记录最终统计
    """
    draft = state.get("generated_draft", "")
    word_count = len(draft)

    logger.info(f"[Commit] Chapter committed. Word count: {word_count}")

    return {
        "current_node": "commit",
        "execution_history": state.get("execution_history", []) + ["commit"],
        "metadata": {
            **state.get("metadata", {}),
            "final_word_count": word_count,
            "status": "completed",
        },
    }


# Re-export agent nodes for graph construction
__all__ = [
    "load_runtime_context_node",
    "context_agent_node",
    "planner_agent_node",
    "writer_agent_node",
    "consistency_agent_node",
    "reviewer_agent_node",
    "rewrite_agent_node",
    "commit_node",
]
