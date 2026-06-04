"""工作流单元测试"""

import pytest

from src.workflows import create_initial_state
from src.workflows.graph import (
    create_novel_workflow,
    should_continue_to_review,
    should_rewrite,
)
from src.workflows.nodes import commit_node, load_runtime_context_node


# ========== State Tests ==========


class TestCreateInitialState:
    def test_basic_fields(self):
        state = create_initial_state("s1", "c1", "u1")
        assert state["story_id"] == "s1"
        assert state["chapter_id"] == "c1"
        assert state["user_id"] == "u1"

    def test_defaults(self):
        state = create_initial_state("s1", "c1")
        assert state["novel_context"] == {}
        assert state["generated_draft"] == ""
        assert state["execution_history"] == []
        assert state["retry_count"] == 0
        assert state["error"] is None


# ========== Conditional Routing Tests ==========


class TestShouldContinueToReview:
    def test_no_issues_commit(self):
        state = {"consistency_report": {"total_issues": 0}}
        assert should_continue_to_review(state) == "commit"

    def test_has_issues_review(self):
        state = {"consistency_report": {"total_issues": 3}}
        assert should_continue_to_review(state) == "review"

    def test_missing_report_commit(self):
        state = {}
        assert should_continue_to_review(state) == "commit"


class TestShouldRewrite:
    def test_high_score_commit(self):
        state = {"review_report": {"score": 85}, "retry_count": 0}
        assert should_rewrite(state) == "commit"

    def test_low_score_rewrite(self):
        state = {"review_report": {"score": 60}, "retry_count": 0}
        assert should_rewrite(state) == "rewrite"

    def test_max_retries_commit(self):
        state = {"review_report": {"score": 50}, "retry_count": 3}
        assert should_rewrite(state) == "commit"

    def test_boundary_score_commit(self):
        state = {"review_report": {"score": 75}, "retry_count": 0}
        assert should_rewrite(state) == "commit"

    def test_boundary_score_rewrite(self):
        state = {"review_report": {"score": 74}, "retry_count": 0}
        assert should_rewrite(state) == "rewrite"


# ========== Node Tests ==========


class TestLoadRuntimeContextNode:
    @pytest.mark.asyncio
    async def test_updates_state(self):
        state = create_initial_state("s1", "c1")
        result = await load_runtime_context_node(state)
        assert result["current_node"] == "load_runtime_context"
        assert "load_runtime_context" in result["execution_history"]
        assert result["metadata"]["initialized"] is True


class TestCommitNode:
    @pytest.mark.asyncio
    async def test_updates_state(self):
        state = create_initial_state("s1", "c1")
        state["generated_draft"] = "这是一个测试草稿内容"
        result = await commit_node(state)
        assert result["current_node"] == "commit"
        assert "commit" in result["execution_history"]
        assert result["metadata"]["status"] == "completed"
        assert result["metadata"]["final_word_count"] > 0


# ========== Graph Construction Tests ==========


class TestWorkflowGraph:
    def test_create_workflow(self):
        app = create_novel_workflow()
        assert app is not None

    def test_graph_has_all_nodes(self):
        app = create_novel_workflow()
        graph = app.get_graph()
        node_names = set(graph.nodes.keys())
        expected = {
            "__start__",
            "__end__",
            "load_runtime_context",
            "novel_context",
            "plan_chapter",
            "generate_draft",
            "check_consistency",
            "review",
            "rewrite",
            "commit",
        }
        assert expected.issubset(node_names)

    def test_graph_mermaid_output(self):
        app = create_novel_workflow()
        mermaid = app.get_graph().draw_mermaid()
        assert "load_runtime_context" in mermaid
        assert "check_consistency" in mermaid
        assert "commit" in mermaid
