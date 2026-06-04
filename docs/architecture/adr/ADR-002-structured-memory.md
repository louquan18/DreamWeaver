# ADR-002: 采用结构化记忆管理长文本上下文

**日期**: 2026-06-04  
**状态**: 已接受  
**决策者**: System Architect  
**替代方案**: N/A

---

## 背景（Context）

长篇网络小说通常超过 **100 万字**（约 300-500 章），单章 3000-5000 字。在生成新章节时，需要参考历史内容以保持：

- **人物一致性** - 性格、能力、关系不能突变
- **世界观一致性** - 修炼体系、势力分布、地理设定
- **情节一致性** - 伏笔回收、因果关系、时间线

**问题**：
1. **Token 窗口限制** - 即使是 Claude-3.5-Sonnet-200k，也只能容纳约 60-70 章
2. **成本问题** - 全量输入历史章节，每次生成消耗数万 Token，成本极高
3. **注意力衰减** - LLM 对长文本中间部分注意力下降，影响质量
4. **查询效率** - 需要快速定位相关历史信息

传统的"全文拼接"方案无法满足长篇创作需求。

---

## 决策驱动因素（Decision Drivers）

1. **成本控制** - 降低每次 LLM 调用的 Token 数量
2. **一致性保证** - 准确检索相关历史信息
3. **查询效率** - 检索响应时间 < 2s
4. **可扩展性** - 支持未来添加更多记忆类型
5. **可维护性** - 结构化数据易于更新和查询

---

## 备选方案（Options Considered）

### 方案 1: 全文拼接

**描述**:  
将最近 N 章的完整内容拼接到 Prompt 中。

```python
async def build_context(story_id: str, current_chapter: int):
    # 加载最近 5 章
    recent_chapters = await db.get_chapters(
        story_id,
        start=current_chapter - 5,
        end=current_chapter
    )
    
    # 拼接完整内容
    context = "\n\n".join([ch.content for ch in recent_chapters])
    
    prompt = f"""
    历史内容：
    {context}
    
    请生成第 {current_chapter} 章...
    """
    
    return prompt
```

**优点**:
- ✅ 实现简单，无需额外处理
- ✅ 保留所有细节信息
- ✅ LLM 可以直接理解

**缺点**:
- ❌ Token 消耗巨大（5 章 × 3000 字 ≈ 15,000 tokens）
- ❌ 成本高昂（每章生成成本 $0.5-1）
- ❌ 无法扩展到更多历史章节
- ❌ 注意力衰减，中间部分信息丢失
- ❌ 无法针对性检索（人物、伏笔等）

**技术风险**: 低  
**实现成本**: 低  
**维护成本**: 低  
**运行成本**: 高（Token 成本）

---

### 方案 2: 全文摘要

**描述**:  
对历史章节生成摘要，输入摘要而非全文。

```python
async def build_context(story_id: str, current_chapter: int):
    recent_chapters = await db.get_chapters(
        story_id,
        start=current_chapter - 10,
        end=current_chapter
    )
    
    # 为每章生成摘要（200 字）
    summaries = []
    for ch in recent_chapters:
        summary = await llm.summarize(ch.content)
        summaries.append(f"第{ch.number}章: {summary}")
    
    context = "\n".join(summaries)
    return context
```

**优点**:
- ✅ 压缩率高（3000 字 → 200 字，约 93%）
- ✅ 可以容纳更多历史章节
- ✅ 成本大幅降低

**缺点**:
- ❌ 摘要可能丢失关键细节
- ❌ 无法针对性检索（人物、伏笔）
- ❌ 摘要生成本身消耗 Token
- ❌ 人物关系变化可能丢失
- ❌ 伏笔信息可能被忽略

**技术风险**: 低  
**实现成本**: 中（需要摘要生成）  
**维护成本**: 中  
**运行成本**: 中

---

### 方案 3: 结构化记忆 + 向量检索

**描述**:  
将历史章节抽取为结构化信息（Timeline/Character/Foreshadow/World），存储到数据库和向量库，生成时按需检索。

```python
# 1. 章节压缩（事件抽取）
async def compress_chapter(chapter: Chapter):
    events = await llm.extract_events(chapter.content)
    character_changes = await llm.extract_character_changes(chapter.content)
    summary = await llm.summarize(chapter.content)
    
    return {
        "chapter_id": chapter.id,
        "summary": summary,  # 200 字
        "events": events,    # 5-10 个关键事件
        "character_changes": character_changes  # 人物状态变化
    }

# 2. 结构化存储
class NovelMemory:
    timeline: List[TimelineEvent]          # 关键事件时间线
    characters: Dict[str, CharacterState]  # 人物当前状态
    foreshadows: List[Foreshadow]         # 活跃伏笔
    world_state: WorldState                # 世界观状态

# 3. 按需检索
async def build_context(story_id: str, query: str):
    # 向量检索相关章节
    relevant_chapters = await vector_search(query, k=5)
    
    # 加载结构化记忆
    timeline = await db.get_timeline(story_id, last_n=10)
    characters = await db.get_characters(story_id)
    foreshadows = await db.get_active_foreshadows(story_id)
    world_state = await db.get_world_state(story_id)
    
    return {
        "timeline": timeline,
        "characters": characters,
        "foreshadows": foreshadows,
        "world_state": world_state,
        "relevant_chapters": relevant_chapters
    }
```

**结构化记忆示例**:

```python
# Timeline（时间线）
{
    "events": [
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
}

# Character Graph（人物状态）
{
    "张三": {
        "current_state": {
            "level": 50,
            "location": "天元城",
            "cultivation": "金丹期"
        },
        "relationships": {
            "李四": {"type": "好友", "closeness": 80},
            "王五": {"type": "敌人", "closeness": -50}
        },
        "last_appeared": 95
    }
}

# Foreshadow Memory（伏笔）
{
    "foreshadows": [
        {
            "id": "foreshadow-001",
            "chapter_planted": 10,
            "content": "神秘老人提到的上古秘境",
            "trigger_condition": "主角达到元婴期",
            "status": "active"
        }
    ]
}

# World State（世界观）
{
    "forces": {
        "天元宗": {"strength": "strong", "attitude": "friendly"},
        "魔教": {"strength": "strong", "attitude": "hostile"}
    },
    "rules": {
        "修炼体系": "炼气 → 筑基 → 金丹 → 元婴",
        "寿命": "金丹期 500 年，元婴期 1000 年"
    }
}
```

**优点**:
- ✅ 压缩率极高（3000 字 → ~800 字结构化数据，约 73%，加上向量检索可达 40%+）
- ✅ 针对性检索（人物、伏笔、事件）
- ✅ 一致性检查便捷（直接查询人物状态）
- ✅ 可扩展性强（可添加新记忆类型）
- ✅ 查询效率高（索引优化）
- ✅ 语义检索（向量检索相关章节）

**缺点**:
- ❌ 实现复杂度高
- ❌ 需要事件抽取（LLM 调用）
- ❌ 需要向量数据库
- ❌ 初期开发成本高

**技术风险**: 中（依赖 LLM 抽取质量）  
**实现成本**: 高（需要设计 Schema + 抽取流水线）  
**维护成本**: 中  
**运行成本**: 低（Token 大幅减少）

---

### 方案 4: RAG（检索增强生成）

**描述**:  
将所有章节向量化，生成时通过语义检索找到相关章节。

```python
from langchain.vectorstores import Chroma
from langchain.embeddings import OpenAIEmbeddings

# 1. 向量化所有章节
embeddings = OpenAIEmbeddings()
vectorstore = Chroma.from_documents(
    documents=all_chapters,
    embedding=embeddings
)

# 2. 检索相关章节
relevant_chapters = vectorstore.similarity_search(
    query="主角的修炼历程",
    k=5
)

# 3. 拼接检索结果
context = "\n\n".join([ch.content for ch in relevant_chapters])
```

**优点**:
- ✅ 语义检索，准确性高
- ✅ 实现相对简单（LangChain 支持）
- ✅ 可扩展到任意数量章节

**缺点**:
- ❌ 检索结果仍是全文，Token 消耗高
- ❌ 无法保证一致性（可能检索不到关键信息）
- ❌ 人物状态需要从文本中提取
- ❌ 伏笔管理困难

**技术风险**: 低  
**实现成本**: 中  
**维护成本**: 低  
**运行成本**: 中

---

## 决策（Decision）

**选择**: 方案 3 - **结构化记忆 + 向量检索**

**理由**:

1. **压缩率目标达成** - 可实现 40%+ 压缩率，大幅降低成本
2. **一致性保障** - 结构化存储人物状态、伏笔、世界观，便于检测一致性
3. **针对性检索** - 可以精确查询"张三当前在哪里"、"有哪些活跃伏笔"
4. **可扩展性** - 未来可添加新的记忆类型（势力关系、道具图谱等）
5. **混合检索** - 结构化记忆（精确）+ 向量检索（语义）结合
6. **长期价值** - 结构化数据可用于数据分析、可视化

虽然初期开发成本较高，但长期来看，结构化记忆系统是唯一能同时满足**成本**、**一致性**、**可扩展性**的方案。

---

## 后果（Consequences）

### 正面影响
- ✅ Token 成本降低 60%+（从 15,000 → 6,000 tokens per generation）
- ✅ 一致性检测准确率提升（直接查询结构化数据）
- ✅ 支持更长篇幅（可管理 500+ 章）
- ✅ 伏笔管理自动化
- ✅ 人物关系图可视化
- ✅ 查询效率高（< 2s）

### 负面影响
- ⚠️ 初期开发周期长（约 2-3 周）
- ⚠️ 依赖 LLM 抽取质量
- ⚠️ 需要维护向量数据库
- ⚠️ 需要定期更新记忆

### 风险与缓解措施

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 事件抽取不准确 | 中 | 中 | 人工审核 + 提示词优化 |
| 向量检索召回率不足 | 中 | 中 | 混合检索（向量+关键词） |
| 人物状态更新遗漏 | 高 | 低 | 每章生成后强制更新 |
| 记忆数据损坏 | 高 | 低 | 定期备份 + 版本控制 |
| 查询性能问题 | 中 | 低 | 索引优化 + 缓存 |

---

## 技术债务（Technical Debt）

**债务 1**: 当前使用 Chroma 作为向量数据库，未来可能需要迁移到生产级方案
- **计划偿还**: MVP 验证后，评估 Pinecone/Qdrant/Weaviate

**债务 2**: 事件抽取 Prompt 可能需要迭代优化
- **计划偿还**: 收集 bad case，持续优化 Prompt

**债务 3**: 记忆更新策略当前为全量更新，可能影响性能
- **计划偿还**: 实现增量更新机制

---

## 实施计划（Implementation Plan）

### 阶段 1: Schema 设计（3 天）
- [ ] 设计 Timeline Schema
- [ ] 设计 Character Graph Schema
- [ ] 设计 Foreshadow Schema
- [ ] 设计 World State Schema
- [ ] 设计数据库表结构

**预计时间**: 3 天  
**负责人**: Context Engineer

### 阶段 2: 抽取流水线（1 周）
- [ ] 实现事件抽取 Agent
- [ ] 实现人物状态抽取 Agent
- [ ] 实现伏笔识别 Agent
- [ ] 测试抽取质量

**预计时间**: 5-7 天  
**负责人**: AI Team

### 阶段 3: 向量检索集成（3 天）
- [ ] 集成 Chroma 向量库
- [ ] 实现章节向量化
- [ ] 实现混合检索

**预计时间**: 3 天  
**负责人**: Python Backend Team

### 阶段 4: Context Builder（3 天）
- [ ] 实现 Context Agent
- [ ] 整合结构化记忆和向量检索
- [ ] 性能优化（缓存、并发）

**预计时间**: 3 天  
**负责人**: AI Team

---

## 验证标准（Validation Criteria）

- [ ] 压缩率 > 40%
- [ ] 查询响应时间 < 2s
- [ ] 一致性检测准确率 > 90%
- [ ] 事件抽取准确率 > 85%
- [ ] 人物状态更新准确率 > 90%
- [ ] 支持 100+ 章节管理
- [ ] 向量检索召回率 > 80%

---

## 参考资料（References）

- [LangChain Memory 文档](https://python.langchain.com/docs/modules/memory/)
- [Chroma 向量数据库](https://www.trychroma.com/)
- [RAG 最佳实践](https://www.anthropic.com/news/retrieval-augmented-generation)
- [Graph Memory for LLMs](https://arxiv.org/abs/2312.xxxxx)

---

## 更新历史（Update History）

| 日期 | 修改内容 | 修改人 |
|------|----------|--------|
| 2026-06-04 | 初始版本 | System Architect |
