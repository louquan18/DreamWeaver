# Checkpoint 机制模板

## Checkpoint 配置

### 1. PostgreSQL Checkpointer（生产环境）

```python
from langgraph.checkpoint.postgres import PostgresSaver
from sqlalchemy.ext.asyncio import create_async_engine

# 创建数据库引擎
engine = create_async_engine(
    "postgresql+asyncpg://user:password@localhost:5432/dreamweaver",
    pool_size=10,
    max_overflow=20
)

# 创建 Checkpointer
checkpointer = PostgresSaver(
    engine=engine,
    table_name="checkpoints"
)

# 编译工作流
app = workflow.compile(checkpointer=checkpointer)
```

### 2. Memory Checkpointer（开发/测试环境）

```python
from langgraph.checkpoint.memory import MemorySaver

# 内存 Checkpointer（仅用于开发和测试）
checkpointer = MemorySaver()

app = workflow.compile(checkpointer=checkpointer)
```

---

## 数据库表结构

PostgreSQL Checkpointer 会自动创建以下表：

```sql
CREATE TABLE checkpoints (
    thread_id TEXT NOT NULL,
    checkpoint_id TEXT NOT NULL,
    parent_checkpoint_id TEXT,
    checkpoint JSONB NOT NULL,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    PRIMARY KEY (thread_id, checkpoint_id)
);

CREATE INDEX idx_checkpoints_thread_id ON checkpoints(thread_id);
CREATE INDEX idx_checkpoints_created_at ON checkpoints(created_at);
```

---

## 基础使用

### 1. 执行工作流（自动保存 Checkpoint）

```python
async def execute_with_checkpoint(story_id: str, chapter_id: str):
    """执行工作流并自动保存 Checkpoint"""
    
    # 创建初始状态
    initial_state = NovelState(
        story_id=story_id,
        chapter_id=chapter_id,
        novel_context={},
        chapter_outline={},
        generated_draft="",
        execution_history=[]
    )
    
    # 配置 thread_id（用于标识工作流实例）
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    # 执行工作流（每个节点执行后自动保存 Checkpoint）
    final_state = await app.ainvoke(initial_state, config)
    
    return final_state
```

### 2. 从 Checkpoint 恢复

```python
async def resume_from_checkpoint(story_id: str, chapter_id: str):
    """从 Checkpoint 恢复执行"""
    
    # 使用相同的 thread_id
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    # 不传入初始状态，LangGraph 会自动从 Checkpoint 恢复
    async for event in app.astream(None, config):
        for node_name, state in event.items():
            print(f"Resumed node: {node_name}")
            yield state
```

### 3. 获取当前状态

```python
async def get_current_state(story_id: str, chapter_id: str):
    """获取工作流当前状态"""
    
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    # 获取状态快照
    state_snapshot = await app.aget_state(config)
    
    return {
        "values": state_snapshot.values,  # 当前状态
        "next": state_snapshot.next,  # 下一个要执行的节点
        "config": state_snapshot.config,  # 配置信息
        "metadata": state_snapshot.metadata  # 元数据
    }
```

---

## 高级用法

### 1. 获取 Checkpoint 历史

```python
async def get_checkpoint_history(
    story_id: str,
    chapter_id: str,
    limit: int = 10
):
    """获取 Checkpoint 历史记录"""
    
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    # 获取历史 Checkpoints
    history = []
    count = 0
    
    async for checkpoint in app.aget_state_history(config):
        if count >= limit:
            break
        
        history.append({
            "checkpoint_id": checkpoint.config["configurable"]["checkpoint_id"],
            "parent_id": checkpoint.parent_config["configurable"].get("checkpoint_id") if checkpoint.parent_config else None,
            "values": checkpoint.values,
            "next": checkpoint.next,
            "metadata": checkpoint.metadata
        })
        
        count += 1
    
    return history
```

### 2. 回滚到指定 Checkpoint

```python
async def rollback_to_checkpoint(
    story_id: str,
    chapter_id: str,
    checkpoint_id: str
):
    """回滚到指定 Checkpoint"""
    
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}",
            "checkpoint_id": checkpoint_id  # 指定要恢复的 Checkpoint
        }
    }
    
    # 从指定 Checkpoint 继续执行
    async for event in app.astream(None, config):
        for node_name, state in event.items():
            print(f"Rolled back to checkpoint {checkpoint_id}, executing: {node_name}")
            yield state
```

### 3. 人工介入恢复

```python
async def resume_with_human_input(
    story_id: str,
    chapter_id: str,
    human_input: Dict[str, Any]
):
    """
    人工介入后恢复执行
    
    使用场景：工作流在某个节点暂停，等待人工审核后继续
    """
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    # 获取当前状态
    current_state = await app.aget_state(config)
    
    # 合并人工输入
    updated_state = {**current_state.values, **human_input}
    
    # 继续执行
    async for event in app.astream(updated_state, config):
        for node_name, state in event.items():
            yield state
```

---

## Checkpoint 元数据

### 添加自定义元数据

```python
async def execute_with_metadata(story_id: str, chapter_id: str):
    """执行工作流并添加元数据"""
    
    initial_state = create_initial_state(story_id, chapter_id)
    
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        },
        "metadata": {
            "user_id": "user-123",
            "model": "gpt-4",
            "started_at": datetime.now().isoformat()
        }
    }
    
    final_state = await app.ainvoke(initial_state, config)
    
    return final_state
```

### 查询带元数据的 Checkpoints

```python
async def list_checkpoints_with_metadata(
    story_id: str,
    chapter_id: str
):
    """列出带元数据的 Checkpoints"""
    
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    checkpoints = []
    async for checkpoint in app.aget_state_history(config):
        checkpoints.append({
            "checkpoint_id": checkpoint.config["configurable"]["checkpoint_id"],
            "metadata": checkpoint.metadata,
            "values": checkpoint.values
        })
    
    return checkpoints
```

---

## Checkpoint 清理

### 清理过期 Checkpoints

```python
from datetime import datetime, timedelta

async def cleanup_old_checkpoints(days: int = 7):
    """
    清理过期的 Checkpoints
    
    Args:
        days: 保留最近 N 天的 Checkpoints
    """
    cutoff_date = datetime.now() - timedelta(days=days)
    
    async with engine.begin() as conn:
        await conn.execute(
            """
            DELETE FROM checkpoints
            WHERE created_at < :cutoff_date
            """,
            {"cutoff_date": cutoff_date}
        )
```

### 清理指定 thread 的 Checkpoints

```python
async def delete_thread_checkpoints(story_id: str, chapter_id: str):
    """删除指定 thread 的所有 Checkpoints"""
    
    thread_id = f"{story_id}-{chapter_id}"
    
    async with engine.begin() as conn:
        await conn.execute(
            """
            DELETE FROM checkpoints
            WHERE thread_id = :thread_id
            """,
            {"thread_id": thread_id}
        )
```

---

## 性能优化

### 1. 减少 Checkpoint 频率

```python
from langgraph.checkpoint import CheckpointAt

# 只在关键节点保存 Checkpoint
app = workflow.compile(
    checkpointer=checkpointer,
    checkpoint_at=[
        "novel_context",  # 上下文构建完成
        "generate_draft",  # 草稿生成完成
        "review"  # 评审完成
    ]
)
```

### 2. 异步保存

```python
# PostgreSQL Checkpointer 默认是异步的
# 如果需要同步等待保存完成，使用 interrupt

async def execute_with_manual_checkpoint(story_id: str, chapter_id: str):
    """手动控制 Checkpoint 保存时机"""
    
    config = {
        "configurable": {
            "thread_id": f"{story_id}-{chapter_id}"
        }
    }
    
    async for event in app.astream(initial_state, config):
        for node_name, state in event.items:
            # 在关键节点后暂停，确保 Checkpoint 已保存
            if node_name in ["novel_context", "generate_draft"]:
                # 暂停，确保 Checkpoint 已写入
                await asyncio.sleep(0.1)
            
            yield state
```

### 3. 压缩状态

```python
def compress_state_for_checkpoint(state: NovelState) -> NovelState:
    """压缩状态以减少存储空间"""
    
    compressed = state.copy()
    
    # 移除冗余数据
    if "novel_context" in compressed:
        context = compressed["novel_context"]
        # 只保存必要信息
        if "recent_chapters" in context:
            context["recent_chapters"] = [
                {"id": ch["id"], "title": ch["title"]}
                for ch in context["recent_chapters"]
            ]
    
    return compressed
```

---

## 监控和告警

### Checkpoint 监控

```python
async def monitor_checkpoint_health():
    """监控 Checkpoint 健康状态"""
    
    async with engine.begin() as conn:
        # 统计 Checkpoint 数量
        result = await conn.execute(
            """
            SELECT 
                COUNT(*) as total,
                COUNT(DISTINCT thread_id) as unique_threads,
                AVG(pg_column_size(checkpoint)) as avg_size
            FROM checkpoints
            WHERE created_at > NOW() - INTERVAL '24 hours'
            """
        )
        
        row = result.fetchone()
        
        return {
            "total_checkpoints": row[0],
            "unique_threads": row[1],
            "avg_checkpoint_size": row[2]
        }
```

### 恢复成功率监控

```python
checkpoint_stats = {
    "total_resumes": 0,
    "successful_resumes": 0,
    "failed_resumes": 0
}

async def resume_with_monitoring(story_id: str, chapter_id: str):
    """带监控的恢复"""
    
    checkpoint_stats["total_resumes"] += 1
    
    try:
        async for event in resume_from_checkpoint(story_id, chapter_id):
            yield event
        
        checkpoint_stats["successful_resumes"] += 1
        
    except Exception as e:
        checkpoint_stats["failed_resumes"] += 1
        logger.error(f"Resume failed: {e}")
        raise
```

---

## 测试

### 测试 Checkpoint 保存

```python
import pytest

@pytest.mark.asyncio
async def test_checkpoint_save():
    """测试 Checkpoint 保存"""
    
    story_id = "test-story"
    chapter_id = "test-chapter"
    
    # 执行工作流
    initial_state = create_initial_state(story_id, chapter_id)
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    await app.ainvoke(initial_state, config)
    
    # 验证 Checkpoint 已保存
    state = await app.aget_state(config)
    assert state.values is not None
```

### 测试 Checkpoint 恢复

```python
@pytest.mark.asyncio
async def test_checkpoint_resume():
    """测试 Checkpoint 恢复"""
    
    story_id = "test-story"
    chapter_id = "test-chapter"
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    
    # 执行到一半
    initial_state = create_initial_state(story_id, chapter_id)
    async for event in app.astream(initial_state, config):
        # 模拟中断
        break
    
    # 恢复执行
    resumed_states = []
    async for event in app.astream(None, config):
        for node_name, state in event.items():
            resumed_states.append(node_name)
    
    # 验证恢复成功
    assert len(resumed_states) > 0
```

---

## 最佳实践

1. **生产环境使用 PostgreSQL** - 内存 Checkpointer 仅用于开发
2. **合理设置 thread_id** - 使用有意义的标识符
3. **定期清理过期数据** - 避免数据库膨胀
4. **压缩状态** - 减少存储和传输开销
5. **监控恢复时间** - 目标 < 10 秒
6. **添加元数据** - 便于追踪和调试
7. **测试恢复流程** - 确保断点恢复可靠
8. **关键节点保存** - 不是每个节点都需要 Checkpoint
