# P2-T4 Phase 4: additionalMemory 动态补充召回

**阶段目标**: 在结构化记忆和最近摘要之外，按当前章节目标动态召回远期相关记忆，填充 `additionalMemory`。  
**优先级**: P2  
**依赖**: Phase 1、Phase 2、Phase 3  
**建议提交**: `feat(memory): add additional memory retrieval context`

---

## 1. 问题

结构化记忆适合保存长期事实，但某些创作场景仍需要远期细节：

- 某个旧场景的具体承诺
- 某段对话中的特殊措辞
- 某个伏笔初次出现时的环境细节
- 某个人物早期行为模式

如果全部靠 `timeline` 和 `summary`，细节可能不足；如果继续传全文，token 成本不可控。

---

## 2. 目标行为

基于当前任务动态构造 query：

```text
story title + chapter goal + confirmedOutline + characters involved + foreshadow actions + authorIntent
```

召回结果填入：

```json
{
  "additionalMemory": [
    {
      "id": "am-1",
      "type": "chapter_summary",
      "chapterNumber": 4,
      "title": "旧镜之约",
      "content": "林烬曾答应沈青不在镜市使用镜火。",
      "reason": "与本章 foreshadowActions 中的镜火代价相关",
      "source": {
        "chapterId": "...",
        "memoryId": "tl-..."
      },
      "score": 0.82
    }
  ]
}
```

---

## 3. 影响文件

Java:

- Phase 1/2/3 新增的 context assembler
- `StoryMemoryService`
- 可能新增：`AdditionalMemoryRetriever`

Python:

- `backend/python-ai/src/memory/vector_store.py`
- `backend/python-ai/src/services/outline_service.py`
- `backend/python-ai/src/services/draft_service.py`
- `backend/python-ai/src/services/consistency_service.py`

测试:

- Java context assembler 测试
- Python vector search 或 fallback retrieval 测试

---

## 4. 任务拆分

### Task 4.1 定义 additionalMemory 合约

字段：

```json
{
  "id": "am-...",
  "type": "timeline|chapter_summary|paragraph|character|world|foreshadow",
  "content": "可直接给模型看的简短内容",
  "chapterNumber": 1,
  "title": "来源标题",
  "reason": "为什么召回",
  "source": {
    "chapterId": "...",
    "memoryId": "...",
    "paragraphIndex": 0
  },
  "score": 0.8
}
```

验收：

- Java/Python 均按 list of object 处理。
- 每条必须有 `content` 和 `source`。

### Task 4.2 第一版规则召回

不立即依赖向量库，先用规则召回：

1. 当前 confirmedOutline.charactersInvolved 命中的人物记忆。
2. 当前 foreshadowActions 引用的伏笔。
3. 当前 chapter goal 涉及的 high/permanent timeline。
4. 最近 summary 中 title 或 summary 命中的关键词。

验收：

- 即使 Chroma 不可用，也能返回 additionalMemory。
- additionalMemory 不超过 8 条。

### Task 4.3 向量召回接入

如果已有 Chroma summary/fulltext：

1. 使用 chapter goal + endingHook + authorIntent 构造 query。
2. 查询 chapter summaries。
3. 必要时查询 fulltext paragraphs。
4. 合并去重。

验收：

- Chroma 不可用时降级为规则召回。
- Chroma 可用时返回带 score 的结果。
- 不把整段长原文无限制塞入 prompt。

### Task 4.4 去重与排序

排序优先级：

1. 与本章 confirmedOutline 直接相关。
2. 与 open foreshadow 相关。
3. high/permanent timeline。
4. 语义 score 高。
5. 章节更近。

去重规则：

- 同一 `memoryId` 只保留一次。
- 同一 chapter summary 和 paragraph 同时命中时，优先保留更具体 paragraph。
- 与 `timeline/characters/world/foreshadows` 完全重复的内容不再进入 additionalMemory。

验收：

- 测试覆盖重复 memoryId 去重。
- 测试覆盖限制最大条数。

### Task 4.5 Prompt 接入

Prompt 需要明确：

```text
additionalMemory 是补充召回材料，用于查找远期细节。
它不能覆盖 confirmedOutline、blueprint.lockedFacts 或 official structured memory。
如果 additionalMemory 与正式记忆冲突，必须以正式记忆为准，并在 review/consistency 中报告。
```

验收：

- outline/draft prompt 单测包含 additionalMemory 区块。
- prompt 中包含优先级说明。

---

## 5. 测试要求

Java 测试：

1. `additionalMemory_ruleRetrieval_returnsRelevantForeshadow`
2. `additionalMemory_deduplicatesMemoryIds`
3. `additionalMemory_limitsToConfiguredMax`
4. `additionalMemory_fallsBackWhenVectorStoreUnavailable`

Python 测试：

1. `test_outline_prompt_contains_additional_memory`
2. `test_draft_prompt_contains_additional_memory_priority_warning`
3. `test_vector_search_returns_bounded_results`

---

## 6. 完成标准

- `additionalMemory` 可由规则召回填充。
- Chroma 可用时可增强召回，不可用时不影响主流程。
- prompt 明确 additionalMemory 的低优先级和补充性质。
- additionalMemory 有来源、原因、score 或规则依据。

