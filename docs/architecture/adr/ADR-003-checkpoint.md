# ADR-003: 使用 Checkpoint 机制实现任务恢复

**日期**: 2026-06-04  
**状态**: 已接受  
**决策者**: System Architect  
**替代方案**: N/A

---

## 背景（Context）

长篇小说章节生成是一个耗时较长的任务，典型的 3000 字章节生成流程包含：

1. **Context Agent** - 加载上下文（10-20s）
2. **Planner Agent** - 章节规划（20-30s）
3. **Writer Agent** - 生成草稿（60-90s）
4. **Consistency Agent** - 一致性检查（15-20s）
5. **Reviewer Agent** - 评审（10-15s）
6. **Rewrite Agent** - 重写（可选，30-60s）

**总耗时**: 2-4 分钟

在此期间可能发生：
- **服务重启** - 部署更新、资源调度
- **网络中断** - LLM API 调用失败
- **模型异常** - Rate Limit、超时
- **用户主动中断** - 用户关闭页面或取消任务

如果没有断点恢复机制，任务中断后需要从头开始，浪费时间和成本。

---

## 决策驱动因素（Decision Drivers）

1. **用户体验** - 避免长时间任务失败后从头开始
2. **成本控制** - 避免重复调用 LLM（已完成的节点不应重复执行）
3. **可靠性** - 保证服务重启后任务可继续
4. **恢复速度** - 目标恢复时间 < 10s
5. **状态完整性** - 确保恢复后状态与中断前一致

---

## 备选方案（Options Considered）

### 方案 1: 无 Checkpoint（从头开始）

**描述**:  
任务中断后，用户需要重新点击"生成"按钮，从 Context Agent 重新开始。

```python
async def generate_chapter(story_id: str, chapter_id: str):
    # 每次都从头开始
    context = await context_agent(story_id)
    outline = await planner_agent(context)
    draft = await writer_agent(outline, context)
    # ...
    return draft
```

**优点**:
- ✅ 实现简单，无需额外逻辑
- ✅ 无状态管理开销

**缺点**:
- ❌ 用户体验差（需要重新等待 2-4 分钟）
- ❌ 成本浪费（重复调用 LLM）
- ❌ 对网络波动敏感
- ❌ 不适合长时间任务

**技术风险**: 低  
**实现成本**: 低  
**维护成本**: 低  
**用户体验**: 差

---

### 方案 2: 简单状态缓存（Redis）

**描述**:  
在每个节点完成后，将状态保存到 Redis，中断后从 Redis 恢复。

```python
async def generate_chapter_with_cache(story_id: str, chapter_id: str):
    task_id = f"{story_id}-{chapter_id}"
    
    # 尝试从 Redis 恢复
    cached_state = await redis.get(f"task:{task_id}")
    
    if cached_state:
        state = json.loads(cached_state)
        # 根据已完成的节点决定从哪里继续
        if "context" not in state:
            context = await context_agent(story_id)
            state["context"] = context
            await redis.set(f"task:{task_id}", json.dumps(state))
        
        if "outline" not in state:
            outline = await planner_agent(state["context"])
            state["outline"] = outline
            await redis.set(f"task:{task_id}", json.dumps(state))
        
        # ...
    else:
        state = {}
        # 正常流程
```

**优点**:
- ✅ 实现相对简单
- ✅ 恢复速度快（Redis 内存存储）
- ✅ 可以断点续传

**缺点**:
- ❌ 需要手动管理状态保存逻辑
- ❌ 代码可读性差（大量 if 判断）
- ❌ 难以维护（新增节点需要修改恢复逻辑）
- ❌ 状态一致性难以保证
- ❌ Redis 数据可能丢失（不持久化）
- ❌ 无法追溯历史状态

**技术风险**: 中  
**实现成本**: 中  
**维护成本**: 高

---

### 方案 3: LangGraph Checkpoint（PostgresSaver）

**描述**:  
使用 LangGraph 内置的 Checkpoint 机制，自动保存状态到 PostgreSQL。

```python
from langgraph.graph import StateGraph
from langgraph.checkpoint.postgres import PostgresSaver

# 配置 Checkpoint
checkpointer = PostgresSaver(
    connection_string="postgresql://user:pass@localhost/dreamweaver"
)

# 编译工作流
workflow = StateGraph(NovelState)
# ... 添加节点 ...
app = workflow.compile(checkpointer=checkpointer)

# 执行（自动保存 Checkpoint）
config = {
    "configurable": {
        "thread_id": f"{story_id}-{chapter_id}"
    }
}

# 初次执行
result = await app.ainvoke(initial_state, config)

# 中断后恢复（不传入初始状态，自动从 Checkpoint 恢复）
result = await app.ainvoke(None, config)
```

**LangGraph Checkpoint 工作原理**:

1. **自动保存** - 每个节点执行完成后，自动保存状态到数据库
2. **版本管理** - 每次保存生成新的 checkpoint_id，形成历史链
3. **自动恢复** - 通过 thread_id 查找最新 Checkpoint，恢复状态
4. **幂等性** - 同一节点重复执行会覆盖之前的结果

**数据结构**:
```sql
CREATE TABLE checkpoints (
    thread_id TEXT,
    checkpoint_ns TEXT DEFAULT '',
    checkpoint_id TEXT,
    parent_checkpoint_id TEXT,
    type TEXT,
    checkpoint BYTEA,  -- 序列化的状态
    metadata BYTEA,
    PRIMARY KEY (thread_id, checkpoint_ns, checkpoint_id)
);
```

**优点**:
- ✅ 开箱即用（LangGraph 内置）
- ✅ 自动保存，无需手动编写逻辑
- ✅ 状态完整性保证（事务支持）
- ✅ 版本管理（可追溯历史）
- ✅ 持久化存储（PostgreSQL）
- ✅ 代码清晰（无额外逻辑）
- ✅ 支持多种存储（PostgreSQL/SQLite/Memory）

**缺点**:
- ❌ 依赖 LangGraph 框架
- ❌ 数据库存储，可能比 Redis 稍慢
- ❌ Checkpoint 数据较大（完整状态序列化）

**技术风险**: 低（官方支持）  
**实现成本**: 低（几乎无需额外代码）  
**维护成本**: 低（框架维护）

---

### 方案 4: Temporal Workflow（持久化工作流）

**描述**:  
使用 Temporal 工作流引擎，天然支持断点恢复。

```python
@workflow.defn
class ChapterGenerationWorkflow:
    @workflow.run
    async def run(self, story_id: str, chapter_id: str):
        # Temporal 自动保存每一步的状态
        context = await workflow.execute_activity(
            context_agent,
            args=[story_id],
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        outline = await workflow.execute_activity(
            planner_agent,
            args=[context],
            start_to_close_timeout=timedelta(seconds=60)
        )
        
        # ...
```

**优点**:
- ✅ 企业级工作流引擎
- ✅ 强大的持久化机制
- ✅ 自动重试和恢复
- ✅ 可视化监控

**缺点**:
- ❌ 需要独立部署 Temporal Server
- ❌ 学习曲线陡峭
- ❌ 运维成本高
- ❌ 对简单场景过于重量级
- ❌ Python SDK 不够成熟

**技术风险**: 中  
**实现成本**: 高  
**维护成本**: 高

---

## 决策（Decision）

**选择**: 方案 3 - **LangGraph Checkpoint (PostgresSaver)**

**理由**:

1. **开箱即用** - 无需编写额外的保存/恢复逻辑
2. **状态完整性** - PostgreSQL 事务保证
3. **版本管理** - 可追溯历史状态
4. **与 LangGraph 集成** - 已选择 LangGraph 作为编排框架（ADR-001）
5. **低维护成本** - 框架维护 Checkpoint 逻辑
6. **恢复速度快** - PostgreSQL 索引优化，< 10s

相比手动 Redis 缓存，LangGraph Checkpoint 更简洁、更可靠。相比 Temporal，更轻量、更易集成。

---

## 后果（Consequences）

### 正面影响
- ✅ 任务中断后可无缝恢复
- ✅ 开发效率提升（无需手动编写恢复逻辑）
- ✅ 用户体验提升（不需要重新等待）
- ✅ 成本节省（避免重复 LLM 调用）
- ✅ 状态可追溯（历史 Checkpoint）

### 负面影响
- ⚠️ 数据库存储开销（每个任务约 50-100KB）
- ⚠️ 需要定期清理历史 Checkpoint
- ⚠️ 依赖 LangGraph 框架

### 风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| Checkpoint 数据库损坏 | 高 | 低 | 定期备份 + 主从复制 |
| Checkpoint 数据过大 | 中 | 中 | 压缩状态 + 定期清理 |
| 恢复时状态版本不匹配 | 中 | 低 | 版本迁移机制 |
| 数据库性能瓶颈 | 中 | 低 | 索引优化 + 读写分离 |

---

## 技术债务（Technical Debt）

**债务 1**: 当前 Checkpoint 包含完整状态，未来可能需要压缩
- **计划偿还**: 监控 Checkpoint 大小，超过 200KB 时实现压缩

**债务 2**: 历史 Checkpoint 未定期清理，可能占用大量存储
- **计划偿还**: 实现定期清理任务（保留最近 7 天）

**债务 3**: Checkpoint 未加密存储，可能存在安全风险
- **计划偿还**: 评估敏感数据，必要时加密存储

---

## 实施计划（Implementation Plan）

### 阶段 1: 配置 PostgresSaver（1 天）
- [ ] 安装 LangGraph PostgreSQL 依赖
- [ ] 配置数据库连接
- [ ] 创建 Checkpoint 表
- [ ] 测试保存和恢复

**预计时间**: 1 天  
**负责人**: Python Backend Team

### 阶段 2: 集成到工作流（1 天）
- [ ] 在 workflow.compile() 时传入 checkpointer
- [ ] 配置 thread_id 生成策略
- [ ] 测试自动保存

**预计时间**: 1 天  
**负责人**: AI Team

### 阶段 3: 恢复逻辑（2 天）
- [ ] 实现任务状态查询 API
- [ ] 实现手动恢复 API
- [ ] 前端恢复按钮
- [ ] 测试完整恢复流程

**预计时间**: 2 天  
**负责人**: Full Stack Team

### 阶段 4: 监控和清理（2 天）
- [ ] 监控 Checkpoint 大小
- [ ] 实现定期清理任务
- [ ] 告警配置

**预计时间**: 2 天  
**负责人**: DevOps Team

---

## 验证标准（Validation Criteria）

- [x] 每个节点执行后自动保存 Checkpoint
- [x] 中断后可从最新 Checkpoint 恢复
- [ ] 恢复时间 < 10s
- [ ] 状态完整性 100%（恢复后与中断前一致）
- [ ] Checkpoint 大小 < 100KB
- [ ] 支持查询历史 Checkpoint
- [ ] 支持手动恢复指定 Checkpoint

---

## 实施示例

### 1. 配置 Checkpoint

```python
# src/core/checkpoint.py
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import create_async_engine

def create_checkpointer():
    """创建 Checkpoint 保存器"""
    engine = create_async_engine(
        "postgresql+asyncpg://user:pass@localhost/dreamweaver",
        echo=False
    )
    
    return PostgresSaver(engine)
```

### 2. 编译工作流

```python
# src/workflows/chapter_generation.py
from langgraph.graph import StateGraph
from src.core.checkpoint import create_checkpointer

workflow = StateGraph(NovelState)

# 添加节点...
workflow.add_node("context", context_agent)
workflow.add_node("planner", planner_agent)
# ...

# 编译时传入 checkpointer
checkpointer = create_checkpointer()
app = workflow.compile(checkpointer=checkpointer)
```

### 3. 执行和恢复

```python
# src/api/chapters.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/chapters/generate")
async def generate_chapter(story_id: str, chapter_id: str):
    """生成章节（带 Checkpoint）"""
    
    # thread_id 用于识别任务
    thread_id = f"{story_id}-{chapter_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 初始状态
    initial_state = NovelState(
        story_id=story_id,
        chapter_id=chapter_id,
        # ...
    )
    
    # 执行（自动保存 Checkpoint）
    result = await app.ainvoke(initial_state, config)
    
    return result

@router.post("/chapters/{chapter_id}/resume")
async def resume_chapter(story_id: str, chapter_id: str):
    """从 Checkpoint 恢复"""
    
    thread_id = f"{story_id}-{chapter_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 不传入初始状态，自动从 Checkpoint 恢复
    result = await app.ainvoke(None, config)
    
    return result

@router.get("/chapters/{chapter_id}/status")
async def get_chapter_status(story_id: str, chapter_id: str):
    """查询任务状态"""
    
    thread_id = f"{story_id}-{chapter_id}"
    config = {"configurable": {"thread_id": thread_id}}
    
    # 获取最新状态
    state_snapshot = await app.aget_state(config)
    
    return {
        "current_node": state_snapshot.next,
        "state": state_snapshot.values,
        "checkpoint_id": state_snapshot.config["configurable"]["checkpoint_id"]
    }
```

### 4. 清理任务

```python
# src/tasks/cleanup.py
from sqlalchemy import text
from src.core.database import get_db

async def cleanup_old_checkpoints():
    """清理 7 天前的 Checkpoint"""
    
    async with get_db() as db:
        await db.execute(
            text("""
                DELETE FROM checkpoints
                WHERE created_at < NOW() - INTERVAL '7 days'
            """)
        )
        await db.commit()
```

---

## 参考资料（References）

- [LangGraph Checkpoint 文档](https://langchain-ai.github.io/langgraph/how-tos/persistence/)
- [PostgresSaver API](https://langchain-ai.github.io/langgraph/reference/checkpoints/#postgressaver)
- [LangGraph State Recovery](https://langchain-ai.github.io/langgraph/how-tos/human-in-the-loop/)

---

## 现状更新（Status Update · 2026-06-17）

> 本节为事实校正，不修改上方原始决策记录。

- **决策方向不变**：仍计划采用 LangGraph Checkpoint（方案 3）。
- **实际尚未落地**：代码当前使用 `MemorySaver()`（内存态），`backend/python-ai/src/workflows/graph.py:95`；`backend/python-ai/src/checkpoint/` 仅含空 `__init__.py`，PostgresSaver 未接线。
- **影响**：MemorySaver 在进程重启后丢失全部状态，因此本 ADR"背景"中列出的"服务重启可恢复"场景**目前不成立**。
- **校正"验证标准"**：上文「验证标准」中被勾选为 `[x]` 的两项（"每个节点执行后自动保存 Checkpoint""中断后可从最新 Checkpoint 恢复"）**实为目标，当前未实现**，不应视为已完成。
- 权威状态见 [STATUS.md](../../STATUS.md) 第 4 节。

---

## 更新历史（Update History）

| 日期 | 修改内容 | 修改人 |
|------|----------|--------|
| 2026-06-04 | 初始版本 | System Architect |
| 2026-06-17 | 追加"现状更新"小节，校正未落地与误标完成项 | louquan |
