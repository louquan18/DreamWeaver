# Workflow 模板

## 完整工作流示例 - 章节生成

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver
from typing import Literal

from .state import NovelState
from .nodes import (
    load_runtime_context_node,
    novel_context_node,
    plan_chapter_node,
    generate_draft_node,
    check_consistency_node,
    review_node,
    rewrite_node,
    commit_node
)

# ========== 创建状态图 ==========
workflow = StateGraph(NovelState)

# ========== 添加节点 ==========
workflow.add_node("load_runtime_context", load_runtime_context_node)
workflow.add_node("novel_context", novel_context_node)
workflow.add_node("plan_chapter", plan_chapter_node)
workflow.add_node("generate_draft", generate_draft_node)
workflow.add_node("check_consistency", check_consistency_node)
workflow.add_node("review", review_node)
workflow.add_node("rewrite", rewrite_node)
workflow.add_node("commit", commit_node)

# ========== 设置入口点 ==========
workflow.set_entry_point("load_runtime_context")

# ========== 添加边（顺序执行）==========
workflow.add_edge("load_runtime_context", "novel_context")
workflow.add_edge("novel_context", "plan_chapter")
workflow.add_edge("plan_chapter", "generate_draft")
workflow.add_edge("generate_draft", "check_consistency")

# ========== 条件路由函数 ==========
def should_continue_to_review(
    state: NovelState
) -> Literal["review", "commit"]:
    """
    决定是否需要评审
    
    如果一致性检查发现问题，进入评审流程
    否则直接提交
    """
    consistency_report = state.get("consistency_report", {})
    total_issues = consistency_report.get("total_issues", 0)
    
    if total_issues > 0:
        return "review"
    else:
        return "commit"


def should_rewrite(
    state: NovelState
) -> Literal["rewrite", "commit"]:
    """
    决定是否需要重写
    
    如果评审分数低于阈值，进入重写流程
    否则提交
    """
    review_report = state.get("review_report", {})
    score = review_report.get("score", 0)
    
    # 分数 >= 80 视为合格
    if score >= 80:
        return "commit"
    else:
        return "rewrite"

# ========== 添加条件边 ==========
workflow.add_conditional_edges(
    "check_consistency",
    should_continue_to_review,
    {
        "review": "review",
        "commit": "commit"
    }
)

workflow.add_conditional_edges(
    "review",
    should_rewrite,
    {
        "rewrite": "rewrite",
        "commit": "commit"
    }
)

# 重写后返回评审
workflow.add_edge("rewrite", "review")

# 提交后结束
workflow.add_edge("commit", END)

# ========== 配置 Checkpoint ==========
checkpointer = PostgresSaver(
    connection_string="postgresql://user:pass@localhost/dreamweaver"
)

# ========== 编译工作流 ==========
app = workflow.compile(checkpointer=checkpointer)
```

---

## 执行工作流

### 1. 基础执行

```python
async def generate_chapter(story_id: str, chapter_id: str, user_id: str):
    """生成章节"""
    
    # 创建初始状态
    initial_state = NovelState(
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
        checkpoint_id=None,
        retry_count=0,
        metadata={}
    )
    
    # 配置（thread_id 用于 Checkpoint）
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    # 执行工作流
    final_state = await app.ainvoke(initial_state, config)
    
    return final_state
```

### 2. 流式执行

```python
async def generate_chapter_stream(
    story_id: str,
    chapter_id: str,
    user_id: str
):
    """生成章节（流式）"""
    
    initial_state = create_initial_state(story_id, chapter_id, user_id)
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    # 流式执行
    async for event in app.astream(initial_state, config):
        # 每个事件是 {node_name: state} 格式
        for node_name, state in event.items():
            print(f"Completed: {node_name}")
            yield {
                "type": "node_complete",
                "node": node_name,
                "state": state
            }
```

### 3. 带事件流的执行

```python
async def generate_chapter_with_events(
    story_id: str,
    chapter_id: str,
    user_id: str
):
    """生成章节（Token 级流式）"""
    
    initial_state = create_initial_state(story_id, chapter_id, user_id)
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    # astream_events 提供更细粒度的事件
    async for event in app.astream_events(initial_state, config, version="v1"):
        event_type = event["event"]
        
        if event_type == "on_llm_stream":
            # LLM Token 流
            chunk = event["data"]["chunk"]
            yield {
                "type": "token",
                "content": chunk.content
            }
        elif event_type == "on_chain_start":
            # 节点开始
            node_name = event["name"]
            yield {
                "type": "node_start",
                "node": node_name
            }
        elif event_type == "on_chain_end":
            # 节点结束
            node_name = event["name"]
            yield {
                "type": "node_end",
                "node": node_name
            }
```

---

## Checkpoint 恢复

### 1. 获取 Checkpoint 状态

```python
async def get_checkpoint_state(story_id: str, chapter_id: str):
    """获取 Checkpoint 状态"""
    
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    # 获取最新状态
    state_snapshot = await app.aget_state(config)
    
    return {
        "state": state_snapshot.values,
        "next_node": state_snapshot.next,
        "checkpoint_id": state_snapshot.config["configurable"]["checkpoint_id"]
    }
```

### 2. 从 Checkpoint 恢复执行

```python
async def resume_from_checkpoint(story_id: str, chapter_id: str):
    """从 Checkpoint 恢复执行"""
    
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    # 不传入初始状态，从 Checkpoint 自动恢复
    async for event in app.astream(None, config):
        for node_name, state in event.items():
            print(f"Resumed: {node_name}")
            yield {
                "type": "node_complete",
                "node": node_name,
                "state": state
            }
```

### 3. 列出所有 Checkpoints

```python
async def list_checkpoints(story_id: str, chapter_id: str):
    """列出所有 Checkpoints"""
    
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    # 获取 Checkpoint 历史
    checkpoints = []
    async for checkpoint in app.aget_state_history(config):
        checkpoints.append({
            "checkpoint_id": checkpoint.config["configurable"]["checkpoint_id"],
            "parent_id": checkpoint.parent_config["configurable"].get("checkpoint_id") if checkpoint.parent_config else None,
            "values": checkpoint.values
        })
    
    return checkpoints
```

---

## 子图（Subgraph）

### 定义子图

```python
# 子图：一致性检查流程
consistency_check_workflow = StateGraph(NovelState)

consistency_check_workflow.add_node("check_characters", check_character_consistency_node)
consistency_check_workflow.add_node("check_world", check_world_consistency_node)
consistency_check_workflow.add_node("check_plot", check_plot_consistency_node)
consistency_check_workflow.add_node("merge_reports", merge_consistency_reports_node)

consistency_check_workflow.set_entry_point("check_characters")
consistency_check_workflow.add_edge("check_characters", "check_world")
consistency_check_workflow.add_edge("check_world", "check_plot")
consistency_check_workflow.add_edge("check_plot", "merge_reports")
consistency_check_workflow.add_edge("merge_reports", END)

consistency_check_graph = consistency_check_workflow.compile()
```

### 在主图中使用子图

```python
# 主图
main_workflow = StateGraph(NovelState)

# 使用子图作为节点
main_workflow.add_node("consistency_check", consistency_check_graph)

# 正常添加边
main_workflow.add_edge("generate_draft", "consistency_check")
main_workflow.add_edge("consistency_check", "review")
```

---

## 并行执行

```python
from langgraph.graph import START

# 并行执行多个任务
workflow = StateGraph(NovelState)

workflow.add_node("task_a", task_a_node)
workflow.add_node("task_b", task_b_node)
workflow.add_node("task_c", task_c_node)
workflow.add_node("merge", merge_results_node)

# 从起点并行启动
workflow.add_edge(START, "task_a")
workflow.add_edge(START, "task_b")
workflow.add_edge(START, "task_c")

# 汇聚到 merge 节点
workflow.add_edge("task_a", "merge")
workflow.add_edge("task_b", "merge")
workflow.add_edge("task_c", "merge")

workflow.add_edge("merge", END)
```

---

## 人工介入（Human-in-the-Loop）

```python
async def review_node_with_human_approval(state: NovelState) -> NovelState:
    """评审节点（需要人工批准）"""
    
    # 自动评审
    review_report = await auto_review(state["generated_draft"])
    
    # 如果评分低，需要人工介入
    if review_report["score"] < 60:
        # 标记为需要人工审核
        state["needs_human_review"] = True
        state["review_report"] = review_report
        
        # 等待人工审核结果
        # (在实际应用中，这里会暂停工作流，等待外部输入)
        return state
    
    state["review_report"] = review_report
    return state


def should_wait_for_human(state: NovelState) -> Literal["wait", "continue"]:
    """检查是否需要等待人工"""
    if state.get("needs_human_review"):
        return "wait"
    return "continue"


workflow.add_conditional_edges(
    "review",
    should_wait_for_human,
    {
        "wait": END,  # 暂停，等待人工输入后恢复
        "continue": "commit"
    }
)
```

---

## 工作流可视化

```python
from IPython.display import Image, display

# 生成工作流图
try:
    display(Image(app.get_graph().draw_mermaid_png()))
except Exception:
    # 如果无法生成图片，输出 Mermaid 代码
    print(app.get_graph().draw_mermaid())
```

---

## 错误处理工作流

```python
async def error_handler_node(state: NovelState) -> NovelState:
    """错误处理节点"""
    
    error = state.get("error")
    retry_count = state.get("retry_count", 0)
    
    if retry_count < 3:
        # 重试
        state["retry_count"] = retry_count + 1
        state["error"] = None
        return state
    else:
        # 放弃，记录失败
        logger.error(f"Failed after {retry_count} retries: {error}")
        state["status"] = "failed"
        return state


def should_retry(state: NovelState) -> Literal["retry", "fail"]:
    """决定是否重试"""
    if state.get("error") and state.get("retry_count", 0) < 3:
        return "retry"
    return "fail"


workflow.add_node("error_handler", error_handler_node)

# 错误时进入错误处理
workflow.add_conditional_edges(
    "generate_draft",
    lambda s: "error" if s.get("error") else "continue",
    {
        "error": "error_handler",
        "continue": "check_consistency"
    }
)

workflow.add_conditional_edges(
    "error_handler",
    should_retry,
    {
        "retry": "generate_draft",  # 重试
        "fail": END  # 失败结束
    }
)
```

---

## 最佳实践

1. **明确节点职责** - 每个节点单一职责
2. **条件路由** - 使用条件边实现复杂流程控制
3. **Checkpoint 配置** - 生产环境使用持久化存储
4. **错误处理** - 关键节点添加错误处理和重试
5. **流式输出** - 长时间任务使用流式输出
6. **子图复用** - 相同逻辑抽取为子图
7. **可视化** - 使用 draw_mermaid 可视化工作流
8. **人工介入** - 关键决策点支持人工审核
