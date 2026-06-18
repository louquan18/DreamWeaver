# ChapterGeneration 需求与表设计

**版本**: v0.1  
**日期**: 2026-06-11  
**状态**: 已确认进入 MVP  
**范围**: 章节生成任务、生成历史文本、生成结果采用、状态追踪。

---

## 1. 设计目标

`ChapterGeneration` 是章节生成闭环里的“任务记录”和“历史版本记录”。它要解决三个问题：

1. 用户生成完章节后，可以重新查询历史生成文本。
2. 同一章节可以多次生成，每次生成都可追踪、可回看、可诊断。
3. Java 后端后续接管业务 API 时，有明确的任务状态和持久化模型。

核心关系：

```text
Story 1 -> N Chapter
Chapter 1 -> N ChapterGeneration
Chapter.current content -> adopted ChapterGeneration.draft
```

---

## 2. 用户故事

### US-001 启动一次章节生成

作为用户，我希望选择小说和章节后启动 AI 生成，这样系统能为该章节创建一次可追踪的生成任务。

验收标准：

- 创建生成任务时必须绑定 `story_id` 和 `chapter_id`。
- 如果小说或章节不存在，返回明确错误。
- 同一章节允许多次生成，每次生成创建独立 `generation_id`。
- 创建后状态为 `queued` 或 `running`。

### US-002 实时查看生成过程

作为用户，我希望在生成过程中看到 token、Agent 节点状态和最终完成事件。

验收标准：

- SSE 事件至少包含 `token`、`node_start`、`node_end`、`done`、`error`。
- 生成记录能保存最终 `execution_history`。
- 失败时生成记录进入 `failed`，并保存 `error_message`。

### US-003 查询历史生成文本

作为用户，我希望重新打开章节时能查看该章节所有历史生成版本，避免生成完后文本丢失。

验收标准：

- 可以按 `story_id + chapter_id` 查询生成历史列表。
- 可以按 `generation_id` 查询单次生成详情。
- 单次详情必须返回完整 `draft`。
- 失败或取消的生成记录也可查询，但 `draft` 可以为空。

### US-004 采用某次生成结果

作为用户，我希望选择某次生成作为章节当前正文，这样章节详情始终返回我采用的版本。

验收标准：

- 只有 `succeeded` 状态的生成记录可以被采用。
- 采用后更新 `chapters.content`、`chapters.word_count`、`chapters.last_generation_id`、`chapters.status`。
- 历史生成记录不删除。
- 查询生成历史列表时能识别哪条记录是当前采用版本。

### US-005 恢复或重新生成

作为用户，我希望失败后可以恢复或重新生成。

验收标准：

- 失败记录保留 `checkpoint_id` 或可用于诊断的执行信息。
- 恢复生成复用原 `generation_id`，重新生成创建新 `generation_id`。
- 失败和取消不会覆盖当前章节正文。

---

## 3. 状态机

### 3.1 状态定义

| 状态 | 说明 | 是否终态 |
| --- | --- | --- |
| `queued` | Java 已创建任务，等待 Python AI 执行 | 否 |
| `running` | Python AI 正在执行工作流 | 否 |
| `succeeded` | 生成完成，并保存了完整结果 | 是 |
| `failed` | 生成失败，保存失败原因 | 是 |
| `cancelled` | 用户或系统取消任务 | 是 |

### 3.2 状态流转

```text
queued -> running -> succeeded
queued -> running -> failed
queued -> cancelled
running -> cancelled
failed -> running   # 恢复同一 generation
```

约束：

- `succeeded`、`cancelled` 不允许再次变为 `running`。
- `failed` 可以恢复为 `running`，但需要保留历史错误信息或追加到执行日志。
- `succeeded` 后才能写入或更新 `chapters.last_generation_id`。

---

## 4. 数据模型

### 4.1 `chapter_generations`

| 字段 | 类型 | 必填 | 说明 |
| --- | --- | --- | --- |
| `id` | UUID | 是 | 生成记录 ID |
| `story_id` | UUID | 是 | 小说 ID，冗余保存便于按小说查询和校验 |
| `chapter_id` | UUID | 是 | 章节 ID |
| `user_id` | UUID | 是 | 发起用户 |
| `status` | VARCHAR(20) | 是 | `queued` / `running` / `succeeded` / `failed` / `cancelled` |
| `request` | JSONB | 是 | 生成请求快照 |
| `draft` | TEXT | 否 | 本次完整生成文本 |
| `draft_url` | TEXT | 否 | 大文本对象存储地址，MVP 可为空 |
| `word_count` | INT | 否 | 本次生成字数 |
| `model_profile` | VARCHAR(50) | 否 | 模型用途配置，如 `writing`、`review` |
| `model_name` | VARCHAR(100) | 否 | 实际写作模型名 |
| `execution_history` | JSONB | 是 | Agent 执行节点历史 |
| `consistency_report` | JSONB | 否 | 一致性检查报告 |
| `review_report` | JSONB | 否 | 质量评审报告 |
| `checkpoint_id` | UUID | 否 | 关联 checkpoint |
| `error_message` | TEXT | 否 | 失败原因 |
| `started_at` | TIMESTAMPTZ | 否 | 开始执行时间 |
| `completed_at` | TIMESTAMPTZ | 否 | 完成、失败或取消时间 |
| `created_at` | TIMESTAMPTZ | 是 | 创建时间 |
| `updated_at` | TIMESTAMPTZ | 是 | 更新时间 |

`request` 建议结构：

```json
{
  "target_words": 3000,
  "extra_prompt": "",
  "model_profile": "writing",
  "auto_adopt": true,
  "source": "web"
}
```

`execution_history` 建议结构：

```json
[
  {"node": "load_runtime_context", "status": "succeeded", "at": "2026-06-11T08:00:00Z"},
  {"node": "generate_draft", "status": "succeeded", "at": "2026-06-11T08:01:00Z"}
]
```

### 4.2 `chapters` 调整

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `content` | TEXT | 当前采用的章节正文 |
| `last_generation_id` | UUID | 当前采用的生成记录 ID |
| `status` | VARCHAR(20) | 建议扩展为 `draft` / `generating` / `generated` / `approved` |

说明：

- `chapters.content` 是当前正文快照，用于章节详情快速查询。
- `chapter_generations.draft` 是每次生成的历史正文。
- 采用历史版本时，不复制或删除历史，只更新 `chapters` 指向和当前正文快照。

---

## 5. PostgreSQL DDL

```sql
CREATE TABLE chapter_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    request JSONB NOT NULL DEFAULT '{}'::jsonb,
    draft TEXT,
    draft_url TEXT,
    word_count INT,
    model_profile VARCHAR(50),
    model_name VARCHAR(100),
    execution_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    consistency_report JSONB,
    review_report JSONB,
    checkpoint_id UUID REFERENCES checkpoints(id) ON DELETE SET NULL,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_chapter_generation_status
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    CONSTRAINT ck_chapter_generation_word_count
        CHECK (word_count IS NULL OR word_count >= 0),
    CONSTRAINT ck_chapter_generation_story_chapter
        UNIQUE (id, story_id, chapter_id)
);

CREATE INDEX idx_chapter_generations_chapter_created
    ON chapter_generations(story_id, chapter_id, created_at DESC);

CREATE INDEX idx_chapter_generations_status_created
    ON chapter_generations(status, created_at DESC);

CREATE INDEX idx_chapter_generations_user_created
    ON chapter_generations(user_id, created_at DESC);

CREATE INDEX idx_chapter_generations_request
    ON chapter_generations USING GIN(request);

ALTER TABLE chapters
    ADD COLUMN last_generation_id UUID NULL;

ALTER TABLE chapters
    ADD CONSTRAINT fk_chapters_last_generation
    FOREIGN KEY (last_generation_id)
    REFERENCES chapter_generations(id)
    ON DELETE SET NULL;
```

如果当前环境没有 `gen_random_uuid()`，需要启用：

```sql
CREATE EXTENSION IF NOT EXISTS pgcrypto;
```

---

## 6. 查询设计

### 6.1 查询章节生成历史列表

输入：

- `story_id`
- `chapter_id`
- `page`
- `page_size`

返回字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 生成记录 ID |
| `status` | 状态 |
| `word_count` | 字数 |
| `model_profile` | 模型用途 |
| `model_name` | 实际模型 |
| `is_adopted` | 是否为当前章节采用版本 |
| `created_at` | 创建时间 |
| `completed_at` | 完成时间 |

`is_adopted` 通过 `chapters.last_generation_id = chapter_generations.id` 计算。

### 6.2 查询生成详情

输入：

- `story_id`
- `chapter_id`
- `generation_id`

返回：

- 基础状态字段。
- 完整 `request`。
- 完整 `draft` 或 `draft_url`。
- `execution_history`。
- `consistency_report`。
- `review_report`。
- `error_message`。

### 6.3 采用生成结果

输入：

- `story_id`
- `chapter_id`
- `generation_id`

事务逻辑：

1. 查询并锁定目标 `chapter_generation`。
2. 校验状态必须为 `succeeded`。
3. 更新 `chapters.content = chapter_generations.draft`。
4. 更新 `chapters.word_count = chapter_generations.word_count`。
5. 更新 `chapters.last_generation_id = chapter_generations.id`。
6. 更新 `chapters.status = 'generated'`。

---

## 7. API 需求

### 7.1 Java Backend 对前端 API

```text
POST /api/stories/{storyId}/chapters/{chapterId}/generations
GET  /api/stories/{storyId}/chapters/{chapterId}/generations
GET  /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}
GET  /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/events
POST /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/adopt
POST /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/resume
POST /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/cancel
```

### 7.2 Python AI Service 内部 API

```text
POST /internal/ai/chapter-generations/{generationId}/start
GET  /internal/ai/chapter-generations/{generationId}/events
POST /internal/ai/chapter-generations/{generationId}/resume
POST /internal/ai/chapter-generations/{generationId}/cancel
```

MVP 过渡期可以继续保留当前 Python 外部生成接口，但前端目标接口应以 Java Backend 为准。

---

## 8. 开发任务拆分

### P0

- 新增 `chapter_generations` 表迁移。
- 给 `chapters` 增加 `last_generation_id` 外键。
- 定义 Java 侧 DTO / Entity / Repository / Service。
- 实现生成任务创建接口。
- 实现生成历史列表和详情查询接口。
- 实现采用生成结果接口。

### P1

- Java 代理或转发 Python SSE。
- Python 生成完成后回传最终结果给 Java。
- 保存 `execution_history`、`consistency_report`、`review_report`。
- 实现失败状态和错误原因保存。

### P2

- 取消生成。
- 恢复同一 generation。
- 将大文本迁移到对象存储。
- 历史版本对比。

---

## 9. 关键决策

1. MVP 默认保留每一次生成历史。
2. 成功生成默认可以自动采用，是否自动采用由 `request.auto_adopt` 控制，MVP 默认 `true`。
3. 章节详情读取 `chapters.content`，历史详情读取 `chapter_generations.draft`。
4. Java 是业务状态的最终写入方；Python 过渡期可临时写库，但目标要改为向 Java 回调或返回结果。
5. `generation_id` 是生成任务、SSE 订阅、日志追踪和 checkpoint 关联的统一业务 ID。

