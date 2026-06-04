---
skill: langgraph-architect
description: LangGraph 工作流架构专家，精通 Agent 编排、State Schema 设计和 Checkpoint 机制
tags: [langgraph, agent, workflow, state-machine, checkpoint]
---

# LangGraph Architect Skill

我是 DreamWeaver 项目的 LangGraph 架构专家，专注于：

## 职责范围

### 1. State Schema 设计
- 定义工作流状态结构（TypedDict）
- 设计状态字段和类型
- 管理状态更新和传递
- 优化状态存储

### 2. Workflow 编排
- 设计 Agent 节点和边
- 定义节点转换条件
- 实现条件路由
- 优化工作流性能

### 3. Checkpoint 机制
- 配置状态持久化
- 实现断点恢复
- 管理 Checkpoint 存储
- 优化恢复性能

### 4. Agent 实现
- 实现各类 Agent 节点
- 集成 LLM 调用
- 实现流式输出
- 错误处理和重试

## 技术栈

### 核心框架
- **LangGraph**: Agent 工作流编排框架
- **LangChain**: LLM 应用开发框架
- **LangSmith**: 可观测性和调试工具

### 支持组件
- **CheckpointSaver**: 状态持久化（PostgreSQL/Redis）
- **MemorySaver**: 内存状态管理
- **StateGraph**: 状态图构建器

## DreamWeaver 工作流架构

### 核心工作流

```
load_runtime_context (加载运行时上下文)
    ↓
novel_context (构建小说上下文)
    ↓
plan_chapter (规划章节)
    ↓
generate_draft (生成草稿)
    ↓
check_consistency (一致性检查)
    ↓
    ├─→ review (评审) ─→ rewrite (重写) ─→ review
    └─→ commit (提交)
```

### State Schema 设计

参考 [state-schema-template.md](state-schema-template.md)

```python
from typing import TypedDict, Optional, List, Dict, Any

class NovelState(TypedDict):
    """小说创作工作流状态"""
    
    # 基础信息
    story_id: str
    chapter_id: str
    
    # 上下文信息
    novel_context: Dict[str, Any]  # 小说上下文（世界观、人物等）
    chapter_outline: Dict[str, Any]  # 章节大纲
    
    # 生成内容
    generated_draft: str  # 生成的草稿
    
    # 检查报告
    consistency_report: Dict[str, Any]  # 一致性报告
    review_report: Dict[str, Any]  # 评审报告
    
    # 执行历史
    execution_history: List[str]  # 执行过的节点
    
    # Checkpoint
    checkpoint_id: Optional[str]  # Checkpoint ID
```

## 工作流实现模式

### 1. 基础节点实现

```python
from langgraph.graph import StateGraph, END
from typing import TypedDict

async def novel_context_node(state: NovelState) -> NovelState:
    """
    构建小说上下文节点
    
    职责：
    - 加载历史章节
    - 提取人物状态
    - 构建时间线
    - 加载世界观
    """
    story_id = state["story_id"]
    
    # 调用 Context Agent
    context = await context_agent.build_context(story_id)
    
    # 更新状态
    state["novel_context"] = context
    state["execution_history"].append("novel_context")
    
    return state
```

### 2. 条件路由实现

```python
def should_rewrite(state: NovelState) -> str:
    """
    决定是否需要重写
    
    根据评审报告决定下一步：
    - 如果质量合格 → "commit"
    - 如果需要修改 → "rewrite"
    """
    review_report = state.get("review_report", {})
    score = review_report.get("score", 0)
    
    if score >= 80:
        return "commit"
    else:
        return "rewrite"
```

### 3. 完整工作流构建

参考 [workflow-template.md](workflow-template.md)

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

# 创建状态图
workflow = StateGraph(NovelState)

# 添加节点
workflow.add_node("load_runtime_context", load_runtime_context_node)
workflow.add_node("novel_context", novel_context_node)
workflow.add_node("plan_chapter", plan_chapter_node)
workflow.add_node("generate_draft", generate_draft_node)
workflow.add_node("check_consistency", check_consistency_node)
workflow.add_node("review", review_node)
workflow.add_node("rewrite", rewrite_node)
workflow.add_node("commit", commit_node)

# 设置入口点
workflow.set_entry_point("load_runtime_context")

# 添加边（顺序执行）
workflow.add_edge("load_runtime_context", "novel_context")
workflow.add_edge("novel_context", "plan_chapter")
workflow.add_edge("plan_chapter", "generate_draft")
workflow.add_edge("generate_draft", "check_consistency")

# 添加条件边
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

# 配置 Checkpoint
checkpointer = PostgresSaver(connection_string=DATABASE_URL)

# 编译工作流
app = workflow.compile(checkpointer=checkpointer)
```

## Checkpoint 机制

参考 [checkpoint-template.md](checkpoint-template.md)

### 1. 配置 Checkpoint

```python
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.memory import MemorySaver

# 生产环境：PostgreSQL
checkpointer = PostgresSaver(
    connection_string=DATABASE_URL,
    table_name="checkpoints"
)

# 开发环境：内存
checkpointer = MemorySaver()
```

### 2. 执行工作流（自动保存）

```python
# 初始状态
initial_state = NovelState(
    story_id="story-123",
    chapter_id="chapter-456",
    novel_context={},
    chapter_outline={},
    generated_draft="",
    consistency_report={},
    review_report={},
    execution_history=[],
    checkpoint_id=None
)

# 执行工作流（自动保存 Checkpoint）
config = {"configurable": {"thread_id": "story-123-chapter-456"}}

async for event in app.astream(initial_state, config):
    print(f"Event: {event}")
```

### 3. 从 Checkpoint 恢复

```python
# 恢复配置（相同的 thread_id）
config = {"configurable": {"thread_id": "story-123-chapter-456"}}

# 获取最新状态
state = await app.aget_state(config)

# 从最新 Checkpoint 继续执行
async for event in app.astream(None, config):
    print(f"Resumed: {event}")
```

## 流式输出

### 使用 astream_events 实现 Token 级流式输出

```python
async def generate_draft_node_stream(state: NovelState) -> NovelState:
    """生成草稿节点（流式输出）"""
    
    outline = state["chapter_outline"]
    context = state["novel_context"]
    
    # 构建 prompt
    prompt = build_writer_prompt(outline, context)
    
    # 流式生成
    draft = ""
    async for event in llm.astream_events(prompt, version="v1"):
        if event["event"] == "on_llm_stream":
            chunk = event["data"]["chunk"]
            draft += chunk.content
            
            # 推送到 SSE（实时展示）
            yield {
                "type": "token",
                "content": chunk.content
            }
    
    # 更新状态
    state["generated_draft"] = draft
    state["execution_history"].append("generate_draft")
    
    return state
```

## Agent 实现示例

### Context Agent

```python
async def context_agent_node(state: NovelState) -> NovelState:
    """
    Context Agent - 构建小说上下文
    
    职责：
    1. 检索历史章节
    2. 提取人物状态
    3. 构建时间线
    4. 加载世界观规则
    """
    story_id = state["story_id"]
    
    # 1. 检索历史章节（最近 5 章）
    recent_chapters = await chapter_repo.get_recent_chapters(story_id, limit=5)
    
    # 2. 提取人物状态
    characters = await character_memory.extract_characters(recent_chapters)
    
    # 3. 构建时间线
    timeline = await timeline_memory.build_timeline(recent_chapters)
    
    # 4. 加载世界观
    world_state = await world_memory.load_world_state(story_id)
    
    # 5. 加载伏笔
    foreshadows = await foreshadow_memory.get_active_foreshadows(story_id)
    
    # 组装上下文
    context = {
        "recent_chapters": recent_chapters,
        "characters": characters,
        "timeline": timeline,
        "world_state": world_state,
        "foreshadows": foreshadows
    }
    
    state["novel_context"] = context
    state["execution_history"].append("novel_context")
    
    return state
```

### Planner Agent

```python
async def planner_agent_node(state: NovelState) -> NovelState:
    """
    Planner Agent - 规划章节
    
    职责：
    1. 分析剧情进度
    2. 设计冲突
    3. 规划情节点
    """
    context = state["novel_context"]
    
    # 构建规划 prompt
    prompt = f"""
    根据以下信息规划下一章节：
    
    时间线：{context["timeline"]}
    人物状态：{context["characters"]}
    伏笔：{context["foreshadows"]}
    
    请规划：
    1. 章节目标
    2. 主要冲突
    3. 关键情节点
    """
    
    # 调用 LLM
    response = await llm.ainvoke(prompt)
    
    # 解析结果
    outline = parse_chapter_outline(response.content)
    
    state["chapter_outline"] = outline
    state["execution_history"].append("plan_chapter")
    
    return state
```

### Writer Agent

```python
async def writer_agent_node(state: NovelState) -> NovelState:
    """
    Writer Agent - 生成章节草稿
    
    职责：
    1. 根据大纲生成章节内容
    2. 流式输出
    """
    outline = state["chapter_outline"]
    context = state["novel_context"]
    
    # 构建写作 prompt
    prompt = f"""
    根据以下大纲和上下文，撰写章节内容：
    
    章节大纲：
    {outline}
    
    人物信息：
    {context["characters"]}
    
    要求：
    - 3000-5000 字
    - 符合人物性格
    - 推进剧情发展
    """
    
    # 生成内容
    response = await llm.ainvoke(prompt)
    draft = response.content
    
    state["generated_draft"] = draft
    state["execution_history"].append("generate_draft")
    
    return state
```

### Consistency Agent

```python
async def consistency_agent_node(state: NovelState) -> NovelState:
    """
    Consistency Agent - 检查一致性
    
    职责：
    1. 人物一致性检查
    2. 世界观一致性检查
    3. 情节一致性检查
    """
    draft = state["generated_draft"]
    context = state["novel_context"]
    
    # 检查人物一致性
    character_issues = await check_character_consistency(
        draft,
        context["characters"]
    )
    
    # 检查世界观一致性
    world_issues = await check_world_consistency(
        draft,
        context["world_state"]
    )
    
    # 检查情节一致性
    plot_issues = await check_plot_consistency(
        draft,
        context["timeline"]
    )
    
    # 生成报告
    report = {
        "character_issues": character_issues,
        "world_issues": world_issues,
        "plot_issues": plot_issues,
        "total_issues": len(character_issues) + len(world_issues) + len(plot_issues)
    }
    
    state["consistency_report"] = report
    state["execution_history"].append("check_consistency")
    
    return state
```

## 错误处理

### 节点错误处理

```python
async def safe_node_wrapper(node_func):
    """节点错误处理包装器"""
    
    async def wrapper(state: NovelState) -> NovelState:
        try:
            return await node_func(state)
        except Exception as e:
            # 记录错误
            logger.error(f"Node error: {e}")
            
            # 更新状态
            state["error"] = str(e)
            state["execution_history"].append(f"error:{node_func.__name__}")
            
            return state
    
    return wrapper

# 使用包装器
workflow.add_node("novel_context", safe_node_wrapper(novel_context_node))
```

### 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10)
)
async def llm_call_with_retry(prompt: str):
    """带重试的 LLM 调用"""
    return await llm.ainvoke(prompt)
```

## 测试

### 单元测试

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_context_agent_node():
    """测试 Context Agent 节点"""
    
    # Mock 依赖
    mock_repo = AsyncMock()
    mock_repo.get_recent_chapters.return_value = [...]
    
    # 初始状态
    state = NovelState(
        story_id="story-123",
        chapter_id="chapter-456",
        novel_context={},
        execution_history=[]
    )
    
    # 执行节点
    result = await context_agent_node(state)
    
    # 断言
    assert "novel_context" in result
    assert "novel_context" in result["execution_history"]
```

## 最佳实践

1. **状态不可变** - 节点返回新状态，不直接修改输入状态
2. **单一职责** - 每个节点只做一件事
3. **错误处理** - 所有节点包含错误处理逻辑
4. **重试机制** - LLM 调用使用重试
5. **Checkpoint 频率** - 关键节点后自动保存
6. **流式输出** - 长时间任务使用流式输出提升体验
7. **可观测性** - 使用 LangSmith 追踪工作流执行

## 相关 Skills

- `/context-engineer` - 上下文管理和记忆系统
- `/python-backend` - 后端集成
- `/test-engineer` - 工作流测试
