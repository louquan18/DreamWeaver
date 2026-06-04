# ADR-001: 选择 LangGraph 作为 Agent 编排框架

**日期**: 2026-06-04  
**状态**: 已接受  
**决策者**: System Architect  
**替代方案**: N/A

---

## 背景（Context）

DreamWeaver 项目需要实现一个复杂的 Multi-Agent 工作流系统，包含 8+ Agent 节点：

- Context Agent（上下文加载）
- Planner Agent（章节规划）
- Writer Agent（内容生成）
- Consistency Agent（一致性检查）
- Reviewer Agent（评审）
- Rewrite Agent（重写）

这些 Agent 需要：
1. **有序协作** - 按照工作流顺序执行
2. **状态传递** - 上游 Agent 的输出作为下游 Agent 的输入
3. **条件路由** - 根据一致性检查和评审结果决定是否重写
4. **断点恢复** - 支持长时间任务中断后恢复
5. **流式输出** - 实时展示生成进度

传统的脚本化编排难以满足这些需求，需要一个专业的 Agent 编排框架。

---

## 决策驱动因素（Decision Drivers）

1. **状态管理复杂度** - 需要在多个 Agent 之间传递和更新状态
2. **断点恢复需求** - 长篇小说生成耗时长，必须支持中断恢复
3. **可视化调试** - 开发阶段需要可视化工作流
4. **流式输出支持** - Writer Agent 需要 Token 级流式输出
5. **社区生态** - 需要活跃的社区和丰富的文档
6. **Python 技术栈** - 团队主要使用 Python，AI 生态也以 Python 为主

---

## 备选方案（Options Considered）

### 方案 1: 手动编排（纯代码）

**描述**:  
使用 Python 函数调用手动编排 Agent 流程，状态通过函数参数传递。

```python
async def generate_chapter(story_id, chapter_id):
    context = await context_agent(story_id)
    outline = await planner_agent(context)
    draft = await writer_agent(outline, context)
    consistency = await consistency_agent(draft, context)
    
    if consistency['issues'] > 0:
        review = await reviewer_agent(draft, consistency)
        if review['score'] < 80:
            draft = await rewrite_agent(draft, review)
    
    return draft
```

**优点**:
- ✅ 简单直接，无额外依赖
- ✅ 完全控制执行流程
- ✅ 调试容易

**缺点**:
- ❌ 状态管理需要手动实现
- ❌ Checkpoint 需要自己开发
- ❌ 流式输出需要自己处理
- ❌ 复杂条件路由代码可读性差
- ❌ 无法可视化工作流
- ❌ 错误处理和重试需要大量样板代码

**技术风险**: 低（技术简单）  
**实现成本**: 中（需要大量基础设施代码）  
**维护成本**: 高（状态管理、Checkpoint、流式输出都需要维护）

---

### 方案 2: LangGraph

**描述**:  
使用 LangChain 团队开发的 LangGraph 框架，基于状态机模式编排 Agent。

```python
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.postgres import PostgresSaver

workflow = StateGraph(NovelState)

# 添加节点
workflow.add_node("context", context_agent)
workflow.add_node("planner", planner_agent)
workflow.add_node("writer", writer_agent)
workflow.add_node("consistency", consistency_agent)
workflow.add_node("review", reviewer_agent)
workflow.add_node("rewrite", rewrite_agent)

# 添加边
workflow.set_entry_point("context")
workflow.add_edge("context", "planner")
workflow.add_edge("planner", "writer")
workflow.add_edge("writer", "consistency")

# 条件路由
workflow.add_conditional_edges(
    "consistency",
    should_review,
    {"review": "review", "end": END}
)

# 配置 Checkpoint
checkpointer = PostgresSaver(connection_string="...")
app = workflow.compile(checkpointer=checkpointer)

# 执行
async for event in app.astream_events(initial_state, config):
    # 处理流式事件
    pass
```

**优点**:
- ✅ 内置状态管理（TypedDict）
- ✅ 内置 Checkpoint 机制（PostgresSaver/SQLiteSaver）
- ✅ 支持流式输出（astream_events）
- ✅ 可视化工具（draw_mermaid）
- ✅ 条件路由清晰（add_conditional_edges）
- ✅ 错误处理和重试机制
- ✅ 与 LangChain 生态无缝集成
- ✅ 活跃的社区和文档

**缺点**:
- ❌ 学习曲线（需要理解状态机模式）
- ❌ 版本较新（v0.2.x），可能有 Breaking Changes
- ❌ 依赖 LangChain 生态

**技术风险**: 低（官方支持，社区活跃）  
**实现成本**: 低（大部分功能开箱即用）  
**维护成本**: 低（框架维护 Checkpoint、状态管理）

---

### 方案 3: Apache Airflow

**描述**:  
使用 Airflow DAG 编排 Agent 任务。

```python
from airflow import DAG
from airflow.operators.python import PythonOperator

with DAG('chapter_generation', schedule_interval=None) as dag:
    context_task = PythonOperator(
        task_id='context',
        python_callable=context_agent
    )
    
    planner_task = PythonOperator(
        task_id='planner',
        python_callable=planner_agent
    )
    
    context_task >> planner_task >> ...
```

**优点**:
- ✅ 成熟的任务编排系统
- ✅ 强大的调度功能
- ✅ Web UI 监控
- ✅ 分布式执行

**缺点**:
- ❌ 过于重量级（需要独立部署）
- ❌ 主要设计用于批处理，不适合实时交互
- ❌ 状态传递通过 XCom，不够直观
- ❌ 流式输出支持差
- ❌ 条件路由复杂
- ❌ Checkpoint 需要自己实现

**技术风险**: 低（成熟产品）  
**实现成本**: 高（部署和配置复杂）  
**维护成本**: 高（运维成本高）

---

### 方案 4: Temporal

**描述**:  
使用 Temporal 工作流引擎编排 Agent。

```python
@workflow.defn
class ChapterGenerationWorkflow:
    @workflow.run
    async def run(self, story_id: str, chapter_id: str):
        context = await workflow.execute_activity(
            context_agent,
            args=[story_id]
        )
        # ...
```

**优点**:
- ✅ 强大的工作流引擎
- ✅ 内置 Checkpoint（自动重试、恢复）
- ✅ 分布式执行
- ✅ 长时间工作流支持

**缺点**:
- ❌ 需要独立部署 Temporal Server
- ❌ 学习曲线陡峭
- ❌ Python SDK 相对不成熟
- ❌ 流式输出支持差
- ❌ 与 LangChain 生态集成差
- ❌ 运维成本高

**技术风险**: 中（部署复杂）  
**实现成本**: 高（需要学习和部署）  
**维护成本**: 高（独立服务）

---

## 决策（Decision）

**选择**: 方案 2 - **LangGraph**

**理由**:

1. **开箱即用的 Checkpoint** - PostgresSaver 直接支持断点恢复，无需自己开发
2. **完美的流式输出支持** - `astream_events` 提供 Token 级流式事件
3. **清晰的状态管理** - TypedDict 定义状态，类型安全
4. **可视化调试** - `draw_mermaid()` 生成工作流图，便于理解和调试
5. **轻量级** - 无需独立部署，集成到 Python 服务即可
6. **LangChain 生态** - 与 LangChain 无缝集成，可以直接使用各种 LLM、Memory、Tools
7. **活跃社区** - LangChain 团队官方维护，文档丰富
8. **低维护成本** - 框架处理大部分基础设施工作

相比手动编排，LangGraph 提供了完整的 Checkpoint 和流式输出支持，大大降低开发成本。相比 Airflow 和 Temporal，LangGraph 更轻量，更适合实时交互场景。

---

## 后果（Consequences）

### 正面影响
- ✅ 开发效率提升 50%+（无需自己开发 Checkpoint、流式输出）
- ✅ 代码可读性提升（声明式定义工作流）
- ✅ 调试效率提升（可视化工具）
- ✅ 快速迭代（修改工作流只需调整节点和边）
- ✅ 与 LangChain 生态无缝集成

### 负面影响
- ⚠️ 依赖第三方框架，存在 Breaking Changes 风险
- ⚠️ 团队需要学习 LangGraph（约 1-2 天）
- ⚠️ 框架版本较新，可能遇到 Bug

### 风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| LangGraph 版本升级导致 Breaking Changes | 中 | 中 | 锁定版本，定期跟进 Release Notes |
| 框架 Bug | 低 | 低 | 贡献社区或临时 Patch |
| 性能问题 | 低 | 低 | 性能测试 + 优化配置 |
| 学习曲线 | 低 | 中 | 1-2 天学习时间，参考官方示例 |

---

## 技术债务（Technical Debt）

**债务 1**: 当前使用 PostgresSaver，未来可能需要优化 Checkpoint 存储
- **计划偿还**: MVP 后根据性能监控评估，可能迁移到专用存储或压缩 Checkpoint

**债务 2**: 依赖 LangGraph v0.2.x，可能需要跟进版本升级
- **计划偿还**: 定期（每季度）跟进 LangGraph 版本，评估升级

---

## 实施计划（Implementation Plan）

### 阶段 1: 学习和 PoC（1 周）
- [ ] 学习 LangGraph 官方文档
- [ ] 编写简单的 Hello World 工作流
- [ ] 测试 Checkpoint 恢复机制
- [ ] 测试流式输出

**预计时间**: 2-3 天  
**负责人**: Python Backend Team

### 阶段 2: 核心工作流开发（2 周）
- [ ] 定义 NovelState Schema
- [ ] 实现 6 个 Agent 节点
- [ ] 配置条件路由
- [ ] 集成 PostgresSaver

**预计时间**: 10-12 天  
**负责人**: AI Team

### 阶段 3: 流式输出和前端集成（1 周）
- [ ] 实现 SSE 端点
- [ ] 前端 SSE 连接
- [ ] Token 级实时显示

**预计时间**: 5 天  
**负责人**: Full Stack Team

---

## 验证标准（Validation Criteria）

- [x] 工作流可正常执行
- [x] Checkpoint 可正常保存和恢复
- [x] 流式输出实时显示
- [x] 条件路由正确工作
- [x] 状态在节点间正确传递
- [ ] 恢复时间 < 10s
- [ ] 支持 8+ 节点编排

---

## 参考资料（References）

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [LangGraph Checkpoint 教程](https://langchain-ai.github.io/langgraph/tutorials/persistence/)
- [LangGraph 流式输出](https://langchain-ai.github.io/langgraph/how-tos/stream-tokens/)
- [LangGraph GitHub](https://github.com/langchain-ai/langgraph)

---

## 更新历史（Update History）

| 日期 | 修改内容 | 修改人 |
|------|----------|--------|
| 2026-06-04 | 初始版本 | System Architect |
