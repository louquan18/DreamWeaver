# P2-T4 Phase 2: recentChapters 摘要压缩

**阶段目标**: 将 `recentChapters` 从“最近 3 章全文”改为“最近 1 章正文 + 最近 N 章摘要”，降低 token 成本并提升上下文稳定性。  
**优先级**: P1  
**依赖**: Phase 1 正式记忆闭环  
**建议提交**: `feat(context): compress recent chapter context with summaries`

---

## 1. 问题

当前 `recentChapters` 默认传最近 3 章完整正文：

```json
[
  {
    "id": "...",
    "chapterNumber": 1,
    "title": "...",
    "content": "完整正文",
    "wordCount": 3200
  }
]
```

问题：

1. token 成本随章节长度快速上升。
2. 历史正文中噪声多，模型容易抓错重点。
3. 远期章节无法靠全文方式持续进入上下文。
4. 与结构化记忆重复，浪费上下文窗口。

---

## 2. 目标行为

目标策略：

```text
recentChapters =
  最近 1 章：正文或结尾片段 + 摘要
  最近 2-5 章：摘要
  更早章节：不进入 recentChapters，通过 timeline/characters/world/foreshadows 或 additionalMemory 进入
```

输出示例：

```json
[
  {
    "id": "...",
    "chapterNumber": 12,
    "title": "镜市夜雨",
    "content": "上一章正文或结尾片段",
    "summary": "上一章摘要",
    "wordCount": 3400,
    "contextRole": "recent_full_text"
  },
  {
    "id": "...",
    "chapterNumber": 11,
    "title": "残镜低语",
    "summary": "第 11 章摘要",
    "wordCount": 3100,
    "contextRole": "recent_summary"
  }
]
```

---

## 3. 影响文件

Java:

- `backend/java-service/src/main/java/com/dreamweaver/service/ChapterGenerationService.java`
- `backend/java-service/src/main/java/com/dreamweaver/service/ChapterOutlineOptionService.java`
- Phase 1 新增的 `StoryMemoryService`
- 新增建议：`ChapterMemorySummary` entity/repository/service

Python:

- `backend/python-ai/src/memory/compression.py`
- `backend/python-ai/src/services/memory_extraction_service.py`
- `backend/python-ai/src/services/draft_service.py`
- `backend/python-ai/src/services/outline_service.py`

测试:

- `backend/java-service/src/test/java/com/dreamweaver/service/ChapterGenerationServiceTests.java`
- `backend/java-service/src/test/java/com/dreamweaver/service/ChapterOutlineOptionServiceTests.java`
- `backend/python-ai/tests/test_memory_extraction_service.py`

---

## 4. 任务拆分

### Task 2.1 定义章节摘要存储

新增章节摘要模型：

```text
chapter_memory_summaries
  id
  story_id
  chapter_id
  chapter_number
  title
  summary
  source_draft_hash
  source_generation_id
  extractor_version
  created_at
  updated_at
```

验收：

- 每个 confirmed chapter 有一条 summary。
- 同一章重复确认不会产生多条冲突 summary。

### Task 2.2 生成 chapterSummary

可选实现路线：

路线 A：在 Python 记忆抽取结果中增加 `chapterSummary`。  
路线 B：Java apply 后调用 Python 单独摘要接口。  
路线 C：短期由 Java 从 `MemoryChangeSet.extractionMetadata.summary` 复用。

推荐第一版使用路线 C，如果现有 summary 足够短且稳定；后续再独立出摘要接口。

验收：

- 第 1 章记忆确认后能保存 chapter summary。
- summary 必须来自 confirmed draft，不得来自未确认草稿。

### Task 2.3 改造 recentChapterContexts

当前相关方法：

- `ChapterGenerationService.recentChapterContexts`
- `ChapterOutlineOptionService.recentChapterContexts`

目标：

1. 抽出公共 context assembler，避免两个 Service 各自实现。
2. 最近 1 章保留 `content`。
3. 最近 2-5 章只传 `summary`。
4. 如果最近 1 章正文超长，按配置裁剪结尾片段。

建议配置：

```text
recentFullTextChapters = 1
recentSummaryChapters = 5
maxRecentFullTextChars = 6000
```

验收：

- 第 6 章生成时，recentChapters 最多 5 条。
- 只有最新一条含 `content`。
- 其余只含 `summary`，不含完整正文。

### Task 2.4 增加 contextMetadata

给 Java 请求增加：

```json
{
  "contextMetadata": {
    "policy": "structured-memory-v1",
    "recentFullTextChapters": 1,
    "recentSummaryChapters": 5,
    "originalRecentChapterChars": 9600,
    "assembledRecentChapterChars": 4200,
    "compressionRate": 0.56
  }
}
```

验收：

- 测试能断言 compressionRate 存在。
- 生成历史 request snapshot 保留 contextMetadata，便于回放。

### Task 2.5 更新 Python prompt

Prompt 需要明确：

1. `summary` 是已确认章节摘要。
2. `content` 只用于最近衔接和文风参考。
3. 如 `summary/content` 与 official memory 冲突，以 official memory 为准。

涉及：

- outline prompt
- draft prompt
- review/consistency prompt 如有使用 recentChapters
- memory extraction prompt

验收：

- prompt 单测包含 `recentChapters.summary` 语义。
- prompt 单测包含 official memory 优先级说明。

---

## 5. 测试要求

Java 单测：

1. `recentChapterContexts_includesOnlyOneFullContentChapter`
2. `recentChapterContexts_usesSummariesForOlderChapters`
3. `recentChapterContexts_includesCompressionMetadata`
4. `missingSummary_fallsBackToShortContentOrEmptySummary`

Python 单测：

1. `test_outline_prompt_uses_recent_chapter_summaries`
2. `test_draft_prompt_mentions_structured_memory_priority`
3. `test_memory_extraction_prompt_accepts_recent_chapter_summary`

---

## 6. 边界情况

1. 老章节没有 summary：
   - 第一版允许临时 fallback 为短摘要占位，但必须标记 `summaryStatus=missing`。
   - 不得伪造“已压缩成功”。

2. 上一章正文过长：
   - 保留结尾片段和 summary。
   - `contentTruncated=true`。

3. 用户重新确认章节：
   - summary 和 source hash 需要更新。
   - 旧 summary 不应继续进入上下文。

---

## 7. 完成标准

- recentChapters 不再默认携带最近 3 章全文。
- 第 2-5 条 recentChapters 使用 summary。
- request snapshot 中可看到 compression metadata。
- 相关 prompt 明确 summary/content/official memory 的优先级。

