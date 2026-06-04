---
skill: context-engineer
description: 上下文工程专家，负责结构化记忆、上下文压缩和时间线管理
tags: [context, memory, compression, timeline, character-graph]
---

# Context Engineer Skill

我是 DreamWeaver 项目的上下文工程专家，专注于：

## 职责范围

### 1. 结构化记忆设计
- Timeline（时间线记忆）
- Character Graph（人物关系图）
- Foreshadow Memory（伏笔记忆）
- World State（世界状态）

### 2. 上下文压缩
- 章节摘要生成
- 事件抽取
- 关键信息提取
- 压缩率优化（目标 40%+）

### 3. 检索优化
- 向量检索
- 关键词检索
- 混合检索策略
- 响应时间优化（目标 < 2s）

## 四层记忆结构

### 1. Timeline（时间线）

**用途**: 记录关键事件的时间顺序

参考 [timeline-template.md](timeline-template.md)

```python
timeline_events = [
    {
        "chapter": 15,
        "event": "主角获得系统",
        "characters": ["主角"],
        "importance": "high"
    },
    {
        "chapter": 20,
        "event": "与反派初次交锋",
        "characters": ["主角", "反派"],
        "importance": "high"
    }
]
```

### 2. Character Graph（人物关系图）

**用途**: 追踪人物状态和关系变化

```python
character_graph = {
    "张三": {
        "name": "张三",
        "current_state": {
            "level": 50,
            "location": "天元城",
            "status": "修炼中"
        },
        "relationships": {
            "李四": {"type": "好友", "closeness": 80},
            "王五": {"type": "敌人", "closeness": -50}
        },
        "personality_traits": ["勇敢", "重情义"],
        "last_appeared": 95
    }
}
```

### 3. Foreshadow Memory（伏笔记忆）

**用途**: 管理伏笔的埋设和回收

```python
foreshadows = [
    {
        "id": "foreshadow-001",
        "chapter_planted": 10,
        "content": "神秘老人提到的上古秘境",
        "trigger_condition": "主角达到 100 级",
        "status": "active",  # active | resolved
        "importance": "high"
    }
]
```

### 4. World State（世界状态）

**用途**: 维护世界观设定和规则

```python
world_state = {
    "forces": {
        "天元宗": {"strength": "strong", "attitude": "friendly"},
        "魔教": {"strength": "strong", "attitude": "hostile"}
    },
    "locations": {
        "天元城": {"description": "主城", "controlled_by": "天元宗"}
    },
    "rules": {
        "修炼体系": "炼气 → 筑基 → 金丹 → 元婴",
        "等级上限": 200
    }
}
```

## 上下文压缩

参考 [compression-template.md](compression-template.md)

### 压缩流程

```python
async def compress_chapter(chapter_content: str) -> Dict[str, Any]:
    """
    压缩章节内容
    
    流程：
    1. 提取关键事件
    2. 提取人物状态变化
    3. 生成摘要
    4. 结构化存储
    """
    
    # 1. 事件抽取
    events = await extract_events(chapter_content)
    
    # 2. 人物状态变化
    character_changes = await extract_character_changes(chapter_content)
    
    # 3. 生成摘要
    summary = await generate_summary(chapter_content)
    
    # 4. 结构化存储
    compressed = {
        "summary": summary,
        "events": events,
        "character_changes": character_changes,
        "original_length": len(chapter_content),
        "compressed_length": len(summary) + len(str(events))
    }
    
    return compressed
```

### 压缩率计算

```python
def calculate_compression_rate(original: str, compressed: Dict) -> float:
    """计算压缩率"""
    original_size = len(original)
    compressed_size = compressed["compressed_length"]
    
    compression_rate = 1 - (compressed_size / original_size)
    return compression_rate  # 目标 > 0.4 (40%)
```

## Memory Schema

参考 [memory-schema-template.md](memory-schema-template.md)

```python
from pydantic import BaseModel
from typing import List, Dict, Optional

class TimelineEvent(BaseModel):
    chapter: int
    event: str
    characters: List[str]
    importance: str  # high | medium | low

class CharacterState(BaseModel):
    name: str
    current_state: Dict[str, Any]
    relationships: Dict[str, Dict[str, Any]]
    personality_traits: List[str]
    last_appeared: int

class Foreshadow(BaseModel):
    id: str
    chapter_planted: int
    content: str
    trigger_condition: str
    status: str  # active | resolved
    importance: str

class WorldState(BaseModel):
    forces: Dict[str, Dict[str, str]]
    locations: Dict[str, Dict[str, str]]
    rules: Dict[str, str]

class NovelMemory(BaseModel):
    timeline: List[TimelineEvent]
    characters: Dict[str, CharacterState]
    foreshadows: List[Foreshadow]
    world_state: WorldState
```

## 检索策略

### 1. 向量检索

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# 构建向量索引
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(
    documents=chapter_summaries,
    embedding=embeddings
)

# 检索相关章节
relevant_chapters = vectorstore.similarity_search(
    query="主角的修炼历程",
    k=5
)
```

### 2. 混合检索

```python
async def hybrid_search(query: str, story_id: str, k: int = 5):
    """混合检索（向量 + 关键词）"""
    
    # 向量检索
    vector_results = await vector_search(query, story_id, k=k)
    
    # 关键词检索
    keyword_results = await keyword_search(query, story_id, k=k)
    
    # 合并去重
    combined = merge_and_rank(vector_results, keyword_results)
    
    return combined[:k]
```

## 性能优化

### 1. 缓存策略

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_character_state(story_id: str, character_name: str):
    """缓存人物状态"""
    return load_character_state(story_id, character_name)
```

### 2. 批量加载

```python
async def load_recent_context(story_id: str, chapters: int = 5):
    """批量加载最近上下文"""
    
    # 并行加载
    timeline_task = load_timeline(story_id, last_n=chapters)
    characters_task = load_characters(story_id)
    foreshadows_task = load_active_foreshadows(story_id)
    world_task = load_world_state(story_id)
    
    timeline, characters, foreshadows, world = await asyncio.gather(
        timeline_task,
        characters_task,
        foreshadows_task,
        world_task
    )
    
    return {
        "timeline": timeline,
        "characters": characters,
        "foreshadows": foreshadows,
        "world_state": world
    }
```

## 最佳实践

1. **结构化优于全文** - 提取结构化信息而非保存全文
2. **增量更新** - 只更新变化的部分
3. **分层存储** - 热数据内存，冷数据数据库
4. **定期压缩** - 历史章节定期压缩
5. **向量索引** - 使用向量检索提高准确性
6. **监控压缩率** - 确保达到 40%+ 压缩率
7. **响应时间** - 检索响应时间 < 2s

## 相关 Skills

- `/langgraph-architect` - 集成到 LangGraph 工作流
- `/novel-skill-engineer` - 小说领域特定知识
- `/python-backend` - 后端实现
