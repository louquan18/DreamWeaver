# P2-T4 Phase 1: 正式记忆 Apply 与读取闭环

**阶段目标**: 作者确认 `MemoryChangeSet` 后，将变更真正应用到正式长期记忆，并在下一章中纲生成和记忆抽取中读取。  
**优先级**: P0  
**建议提交**: `feat(memory): apply confirmed memory changes to official snapshot`

---

## 1. 问题

当前系统已经能从确认正文中抽取 `MemoryChangeSet`，也能让作者确认或编辑。但确认后的变更主要停留在 `MemoryChangeSet` 记录里，还没有稳定进入正式长期记忆。

结果是：

- 下一章中纲生成读不到上一章确认后的结构化记忆。
- `existingMemory` 仍为空，记忆抽取无法判断 add/update/conflict。
- `baseMemoryFingerprint` 固定为 `sha256("{}")`，无法证明抽取时基于哪个记忆版本。

---

## 2. 目标行为

确认记忆后：

```text
MemoryChangeSet.pending
  -> confirm
  -> apply timeline/character/world/foreshadow changes
  -> update official memory snapshot
  -> update baseMemoryFingerprint
  -> chapter workflow moves forward
```

下一章生成中纲时：

```text
ChapterOutlineOptionService.generate
  -> read official memory snapshot
  -> fill timeline/characters/world/foreshadows
  -> send to Python outline-options/generate
```

记忆抽取时：

```text
MemoryChangeSetService.extract
  -> read official memory snapshot
  -> fill existingMemory
  -> send to Python memory-changes/extract
```

---

## 3. 影响文件

Java:

- `backend/java-service/src/main/java/com/dreamweaver/service/MemoryChangeSetService.java`
- `backend/java-service/src/main/java/com/dreamweaver/service/ChapterOutlineOptionService.java`
- `backend/java-service/src/main/java/com/dreamweaver/dto/AiMemoryExtractionRequest.java`
- 新增建议：`backend/java-service/src/main/java/com/dreamweaver/service/StoryMemoryService.java`
- 新增建议：`backend/java-service/src/main/java/com/dreamweaver/entity/StoryMemorySnapshot.java`
- 新增建议：`backend/java-service/src/main/java/com/dreamweaver/repository/StoryMemorySnapshotRepository.java`

Python:

- `backend/python-ai/src/api/routes/memory_changes.py`
- `backend/python-ai/src/services/memory_extraction_service.py`
- `backend/python-ai/src/services/memory_conflict_service.py`

测试:

- `backend/java-service/src/test/java/com/dreamweaver/service/MemoryChangeSetServiceTests.java`
- `backend/java-service/src/test/java/com/dreamweaver/service/ChapterOutlineOptionServiceTests.java`
- `backend/python-ai/tests/test_memory_route.py`
- `backend/python-ai/tests/test_memory_extraction_service.py`

---

## 4. 任务拆分

### Task 1.1 定义正式记忆 snapshot

新增正式记忆 snapshot 模型，第一版可以使用 JSON 字段，避免过早拆表。

建议字段：

```text
id
story_id
schema_version
timeline_json
characters_json
world_json
foreshadows_json
fingerprint_hash
created_at
updated_at
```

验收：

- 能按 `storyId` 创建或读取唯一最新 snapshot。
- 空 story 返回空 snapshot，而不是 null。

### Task 1.2 实现 StoryMemoryService

新增服务：

```text
StoryMemoryService
  getSnapshot(storyId)
  applyChangeSet(changeSet)
  buildExistingMemory(storyId)
  buildOutlineMemoryContext(storyId, chapter)
  fingerprint(memory)
```

验收：

- 空 snapshot 可以正常返回：

```json
{
  "timeline": [],
  "characters": [],
  "world": [],
  "foreshadows": []
}
```

- fingerprint 对相同内容稳定，对不同内容变化。

### Task 1.3 实现 timeline apply

处理：

- `operation=add`
- `operation=update`

规则：

1. add 时生成或保留 `changeId`/memory id。
2. update 必须能定位已有 memory id。
3. 记录 `chapterId`、`chapterNumber`、`sourceGenerationId`、evidence。

验收：

- 确认第 1 章 timeline change 后，snapshot.timeline 增加对应事件。
- 重复 confirm 不应重复添加事件。

### Task 1.4 实现 character apply

规则：

1. 按人物名或 character id 合并。
2. 空值不覆盖已有值。
3. list 字段追加去重。
4. relationships 按 target 合并。
5. 更新 `lastAppearedChapter`。

验收：

- 第 1 章更新主角能力后，第 2 章上下文能读取到该能力。
- 第二次更新 location 不会清空 cultivationLevel。

### Task 1.5 实现 world apply

规则：

1. 支持 rule/location/force 三类 world fact。
2. `locked=true` 的事实被更新时必须保留 evidence。
3. 冲突由 conflict service 提示，apply 阶段不默默覆盖关键事实。

验收：

- 新增 world rule 后，中纲请求的 `world` 含该 rule。
- 修改 locked fact 时测试覆盖冲突或显式 update。

### Task 1.6 实现 foreshadow apply

支持操作：

- add
- update
- resolve
- deprecate

状态：

```text
planned
planted
reinforced
triggered
revealed
resolved
abandoned
```

验收：

- resolved/abandoned 不进入 open foreshadow context。
- overdue/needsAttention 伏笔排序靠前。

### Task 1.7 MemoryChangeSetService 接入 apply

在 confirm 或 freeze 流程中调用正式 apply。

建议策略：

- 如果产品语义是“confirm memory 后即写正式记忆”，则 `confirm()` 内 apply。
- 如果产品语义是“freeze 才最终锁定”，则 `freeze()` 内 apply。

推荐选择：`confirm()` apply，`freeze()` 只负责章节最终锁定。

验收：

- apply 成功后 `MemoryChangeSet.status=CONFIRMED`。
- apply 失败时 `MemoryChangeSet.status=PENDING`，Chapter 不推进。

### Task 1.8 existingMemory 传真实内容

修改 `MemoryChangeSetService.pythonRequest()`：

当前：

```java
Map.of()
```

目标：

```java
storyMemoryService.buildExistingMemory(storyId)
```

验收：

- Python memory extraction request 中 `existingMemory.timeline` 不再固定为空。
- `baseMemoryFingerprint` 使用真实 memory hash。

### Task 1.9 中纲生成填充结构化字段

修改 `ChapterOutlineOptionService.generate()`：

当前：

```java
List.of(), List.of(), List.of(), List.of(), List.of()
```

目标：

```java
memoryContext.timeline()
memoryContext.characters()
memoryContext.world()
memoryContext.foreshadows()
memoryContext.additionalMemory()
```

验收：

- 生成第 2 章中纲时，Python 请求包含第 1 章确认后的 memory。

---

## 5. 接口示例

### 5.1 existingMemory

```json
{
  "timeline": [
    {
      "id": "tl-1",
      "chapterNumber": 1,
      "event": "林烬获得残镜。",
      "importance": "high",
      "isPermanent": true
    }
  ],
  "characters": [
    {
      "name": "林烬",
      "currentState": {
        "location": "镜市",
        "specialAbilities": ["镜火"]
      }
    }
  ],
  "world": [],
  "foreshadows": [],
  "fingerprint": {
    "algorithm": "sha-256",
    "hash": "..."
  }
}
```

---

## 6. 测试要求

Java 单测：

1. `applyConfirmedTimelineChange_updatesSnapshot`
2. `applyCharacterChange_mergesWithoutClearingExistingFields`
3. `confirmedForeshadowResolved_isExcludedFromOpenContext`
4. `memoryExtractionRequest_includesExistingMemory`
5. `outlineGenerationRequest_includesOfficialMemory`
6. `applyFailure_keepsChangeSetPending`

Python 单测：

1. `test_memory_extraction_prompt_contains_existing_memory`
2. `test_conflict_detection_uses_existing_memory`
3. `test_outline_route_accepts_structured_memory_fields`

---

## 7. 完成标准

- `existingMemory` 不再固定为空。
- 中纲生成请求能看到正式 `timeline/characters/world/foreshadows`。
- confirmed memory 能被下一章读取。
- apply 失败不会冻结章节。
- 单元测试覆盖 add/update/resolve/deprecate 的核心路径。

