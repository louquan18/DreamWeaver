# P2-T4 Phase 3: 草稿生成接入结构化记忆

**阶段目标**: 让正文草稿生成直接消费 `timeline/characters/world/foreshadows/additionalMemory`，而不是只依赖 `recentChapters`、蓝图和已确认中纲。  
**优先级**: P1  
**依赖**: Phase 1、Phase 2  
**建议提交**: `feat(draft): pass structured memory to draft generation`

---

## 1. 问题

当前草稿生成请求字段主要是：

- `story`
- `chapter`
- `blueprint`
- `confirmedOutline`
- `recentChapters`
- `extraPrompt`
- `targetWords`
- `modelProfile`

缺少显式结构化记忆字段，导致 Writer Agent 难以稳定利用长期人物状态、世界规则、伏笔状态和关键时间线。

---

## 2. 目标行为

草稿生成请求新增：

```json
{
  "timeline": [],
  "characters": [],
  "world": [],
  "foreshadows": [],
  "additionalMemory": [],
  "contextMetadata": {}
}
```

Writer prompt 中上下文优先级：

```text
confirmedOutline > blueprint.lockedFacts > structured memory > recentChapters > additionalMemory > extraPrompt
```

其中 `extraPrompt` 可以影响写法和局部偏好，但不能覆盖 confirmed facts。

---

## 3. 影响文件

Java:

- `backend/java-service/src/main/java/com/dreamweaver/controller/ChapterGenerationController.java`
- `backend/java-service/src/main/java/com/dreamweaver/service/ChapterGenerationService.java`
- Phase 1/2 新增的 context assembler

Python:

- `backend/python-ai/src/schemas/draft.py`
- `backend/python-ai/src/api/routes/drafts.py`
- `backend/python-ai/src/services/draft_service.py`
- `backend/python-ai/tests/test_draft_route.py`

测试:

- `backend/java-service/src/test/java/com/dreamweaver/controller/ChapterGenerationControllerTests.java`
- `backend/java-service/src/test/java/com/dreamweaver/service/ChapterGenerationServiceTests.java`
- `backend/python-ai/tests/test_draft_route.py`

---

## 4. 任务拆分

### Task 3.1 扩展 Java draft payload

修改 `ChapterGenerationController.pythonDraftRequest()`，从 `writing_context` 中透传：

- `timeline`
- `characters`
- `world`
- `foreshadows`
- `additionalMemory`
- `contextMetadata`

验收：

- Controller 测试断言 payload 包含这些字段。
- 旧 generation request 没有这些字段时仍能正常发送空列表。

### Task 3.2 ChapterGenerationService 写入完整 writing_context

在创建 generation 时，`buildWritingContext()` 不只写：

- `story`
- `chapter`
- `blueprint`
- `confirmedOutline`
- `recentChapters`

还要写：

- `timeline`
- `characters`
- `world`
- `foreshadows`
- `additionalMemory`
- `contextMetadata`

验收：

- generation request snapshot 中保留完整上下文。
- 重新打开生成历史可以复现当时上下文。

### Task 3.3 扩展 Python DraftGenerateRequest

在 `backend/python-ai/src/schemas/draft.py` 中新增可选字段：

```python
timeline: list[dict[str, Any]] = Field(default_factory=list)
characters: list[dict[str, Any]] = Field(default_factory=list)
world: list[dict[str, Any]] = Field(default_factory=list)
foreshadows: list[dict[str, Any]] = Field(default_factory=list)
additional_memory: list[dict[str, Any]] = Field(default_factory=list, alias="additionalMemory")
context_metadata: dict[str, Any] = Field(default_factory=dict, alias="contextMetadata")
```

验收：

- 老请求兼容。
- 字符串化 JSON 被拒绝或规范化为错误。

### Task 3.4 更新 draft prompt

Prompt 需要单独呈现：

```text
[structuredTimeline]
[characterStates]
[worldFacts]
[openForeshadows]
[additionalMemory]
```

并加入约束：

```text
不要重置 characterStates 中的能力、位置、关系和伤势。
不要违反 worldFacts 中 locked=true 的规则。
openForeshadows 中 status=triggered/revealed/needsAttention 的伏笔需要优先考虑。
如果 recentChapters 与 structured memory 冲突，以 structured memory 为准。
```

验收：

- Python prompt 单测能看到 `characters`、`world`、`foreshadows` 内容。
- prompt 中包含冲突优先级说明。

### Task 3.5 控制 Writer 上下文预算

Writer 不应无脑拼接所有结构化记忆。

建议限制：

- timeline: 20
- characters: 12
- world facts: 20
- foreshadows: 10
- additionalMemory: 8

验收：

- 超出限制时 Java assembler 已裁剪。
- Python prompt 不再二次扩张上下文。

---

## 5. 测试要求

Java 测试：

1. `pythonDraftRequest_includesStructuredMemoryFields`
2. `buildWritingContext_includesOfficialMemorySnapshot`
3. `oldGenerationRequest_withoutMemoryFields_defaultsToEmptyLists`

Python 测试：

1. `test_internal_draft_stream_accepts_structured_memory`
2. `test_confirmed_outline_draft_prompt_contains_character_states`
3. `test_confirmed_outline_draft_prompt_contains_open_foreshadows`
4. `test_confirmed_outline_draft_prompt_prioritizes_structured_memory`

---

## 6. 完成标准

- 草稿生成 payload 包含结构化记忆字段。
- Python draft schema 和 prompt 消费这些字段。
- 老请求保持兼容。
- 测试证明人物状态、世界规则、伏笔可进入 Writer prompt。

