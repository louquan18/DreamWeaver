# DreamWeaver 需求确认与后端边界

**版本**: v0.2  
**日期**: 2026-06-11  
**状态**: 已确认 MVP 第一批需求  
**目标**: 把当前原型能力收敛成可开发、可验收的 MVP 需求，并明确 Java 后端与 Python AI 服务的职责边界。

---

## 1. 当前确认的问题

当前系统已经能围绕 `story_id` 和 `chapter_id` 触发章节生成，生成过程可以通过 SSE 返回实时文本。现阶段需求还没有完全落到产品设计里，主要缺口是：

1. 生成完成后，用户需要能查询历史生成文本。
2. 生成任务本身需要可追踪，不能只是一次接口调用后返回一段文本。
3. 后续希望 Java 承担业务后端，但当前小说、章节、生成结果保存等能力主要在 Python FastAPI 原型里。
4. Python 服务需要从“业务 API + AI 编排”逐步收敛为“AI 运行时/Worker”，由 Java 统一对前端暴露业务接口。

---

## 2. MVP 用户目标

MVP 阶段先解决一个闭环：

> 用户选择一部小说和一个章节，启动 AI 生成，实时看到生成过程，生成完成后能在历史记录里再次查看该章节文本。

暂不扩展到完整的小说工作台、复杂编辑器、多版本对比、人工审核流和发布平台。

---

## 3. 核心业务对象

### 3.1 Novel / Story

小说是章节、设定、记忆和生成任务的归属主体。

MVP 字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 小说 ID |
| `user_id` | 所属用户，MVP 可先固定或模拟 |
| `title` | 小说标题 |
| `description` | 简介 |
| `genre` | 题材 |
| `status` | `draft` / `writing` / `completed` |
| `created_at` / `updated_at` | 创建与更新时间 |

### 3.2 Chapter

章节是最终可查询、可编辑、可沉淀进上下文记忆的文本单元。

MVP 字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 章节 ID |
| `story_id` | 所属小说 ID |
| `chapter_number` | 章节序号 |
| `title` | 章节标题 |
| `content` | 当前章节正文 |
| `word_count` | 字数 |
| `status` | `draft` / `generating` / `generated` / `approved` |
| `last_generation_id` | 最近一次成功生成记录 ID |
| `created_at` / `updated_at` | 创建与更新时间 |

### 3.3 ChapterGeneration

生成记录用于保存每一次 AI 生成的输入、状态、结果和执行信息。它解决“生成完了之后没有历史生成文本”的问题。

MVP 字段：

| 字段 | 说明 |
| --- | --- |
| `id` | 生成记录 ID |
| `story_id` | 小说 ID |
| `chapter_id` | 章节 ID |
| `user_id` | 发起用户 |
| `status` | `queued` / `running` / `succeeded` / `failed` / `cancelled` |
| `request` | 本次生成参数快照，例如模型、目标字数、额外提示 |
| `draft` | 本次生成出的完整文本 |
| `word_count` | 本次生成字数 |
| `execution_history` | Agent 节点执行历史 |
| `consistency_report` | 一致性检查结果 |
| `review_report` | 评审结果 |
| `checkpoint_id` | 关联 checkpoint |
| `error_message` | 失败原因 |
| `started_at` / `completed_at` | 执行时间 |
| `created_at` / `updated_at` | 记录时间 |

说明：

- `chapters.content` 保存“当前采用的章节正文”。
- `chapter_generations.draft` 保存“每一次生成的历史文本”。
- 同一个章节可以有多次生成记录，方便后续做重新生成、版本对比和人工选择。

---

## 4. MVP 功能需求

### FR-001 创建和查询小说

用户可以创建小说，并查询小说列表和详情。

验收标准：

- 可以创建一部小说。
- 可以按用户查询小说列表。
- 可以查询小说详情。

### FR-002 创建和查询章节

用户可以在小说下创建章节，并查询章节列表和详情。

验收标准：

- 可以按 `story_id` 创建章节。
- 可以按 `story_id` 查询章节列表。
- 可以按 `story_id + chapter_id` 查询章节详情。
- 章节详情返回当前正文 `content`。

### FR-003 启动章节生成

用户可以基于 `story_id + chapter_id` 启动一次章节生成。

验收标准：

- 请求进入系统后创建一条 `ChapterGeneration` 记录。
- 生成记录状态从 `queued` / `running` 变为 `succeeded` 或 `failed`。
- 生成过程能通过 SSE 返回 token、节点状态和完成事件。
- 生成完成后，保存完整生成文本到 `chapter_generations.draft`。
- 若本次结果被系统自动采用，则同步更新 `chapters.content` 和 `chapters.last_generation_id`。

### FR-004 查询生成记录

用户可以查询某部小说、某个章节下的生成历史。

验收标准：

- 可以按 `story_id + chapter_id` 查询生成记录列表。
- 列表包含生成时间、状态、字数、模型、是否被当前章节采用。
- 可以按 `generation_id` 查询某次生成详情。
- 生成详情返回完整历史文本 `draft` 和执行报告。

### FR-005 查询当前章节文本

用户可以在生成结束后重新打开章节，看到当前采用的章节正文。

验收标准：

- `GET chapter detail` 返回 `content`。
- 即使 SSE 页面关闭，刷新后仍能查询到已完成文本。
- 如果该章节有多次生成，默认显示 `chapters.content`，历史版本从生成记录查询。

### FR-006 失败与恢复

生成失败时，用户能看到失败状态；后续可从 checkpoint 恢复或重新生成。

验收标准：

- 失败记录保留 `error_message`。
- 失败不会覆盖原有 `chapters.content`。
- 失败记录可以被查询。
- 恢复接口可复用 `generation_id` 或 `checkpoint_id`。

---

## 5. 非目标范围

MVP 暂不做：

- 多人协作和复杂权限体系。
- 完整章节编辑器和富文本排版。
- 发布、订阅、付费阅读等小说平台能力。
- 多版本 diff 对比 UI。
- 复杂人工审核工作流。
- 训练或管理大型题材语料库。

这些能力可以在生成闭环稳定后进入后续阶段。

---

## 6. 服务边界确认

### 6.1 目标架构

目标形态：

```text
Frontend
  -> Java Backend
      -> PostgreSQL / Redis
      -> Python AI Service
```

Java 后端是对前端的统一业务入口。Python AI 服务只负责 AI 工作流执行，不直接承载用户侧业务管理。

### 6.2 Java Backend 职责

Java 负责：

- 用户、权限、审计。
- 小说 CRUD。
- 章节 CRUD。
- 生成任务创建与状态管理。
- 生成历史查询。
- 当前章节正文查询。
- 对外 SSE 接口或 SSE 代理。
- 调用 Python AI 服务并落库最终业务状态。

### 6.3 Python AI Service 职责

Python 负责：

- LangGraph Agent 工作流。
- 上下文构建与压缩。
- 一致性检查、评审、重写。
- LLM Provider 与模型路由。
- Checkpoint 快照。
- 向 Java 回传 token、节点事件、最终结果和报告。

Python 不应长期负责：

- 用户体系。
- 小说和章节主数据 CRUD。
- 生成历史的业务查询接口。
- 前端直接依赖的业务 API。

### 6.4 迁移策略

当前 Python 原型可以继续保留，但需要分阶段迁移：

1. 短期：Python 继续提供 `/api/ai/chapters/generate-stream`，并补齐生成结果保存。
2. 过渡期：Java 增加对外 API，内部调用 Python AI 服务；前端改为只调用 Java。
3. 目标期：Python 的公开 API 改为内部 RPC/HTTP Worker API，由 Java 管理任务、状态和历史记录。

---

## 7. 建议 API 设计

### 7.1 前端调用 Java Backend

```text
POST   /api/stories
GET    /api/stories
GET    /api/stories/{storyId}

POST   /api/stories/{storyId}/chapters
GET    /api/stories/{storyId}/chapters
GET    /api/stories/{storyId}/chapters/{chapterId}

POST   /api/stories/{storyId}/chapters/{chapterId}/generations
GET    /api/stories/{storyId}/chapters/{chapterId}/generations
GET    /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}
GET    /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/events
POST   /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/resume
POST   /api/stories/{storyId}/chapters/{chapterId}/generations/{generationId}/adopt
```

说明：

- `POST generations` 创建一次生成任务。
- `GET generations/{generationId}/events` 用 SSE 订阅生成过程。
- `POST adopt` 将某次历史生成结果设为当前章节正文。

### 7.2 Java 调用 Python AI Service

```text
POST   /internal/ai/chapter-generations/{generationId}/start
GET    /internal/ai/chapter-generations/{generationId}/events
POST   /internal/ai/chapter-generations/{generationId}/resume
```

内部请求需要包含：

```json
{
  "generation_id": "uuid",
  "story_id": "uuid",
  "chapter_id": "uuid",
  "user_id": "uuid",
  "request": {
    "target_words": 3000,
    "extra_prompt": "",
    "model_profile": "writing"
  }
}
```

Python 最终返回：

```json
{
  "generation_id": "uuid",
  "status": "succeeded",
  "draft": "...",
  "word_count": 3000,
  "execution_history": ["load_runtime_context", "novel_context", "plan_chapter", "generate_draft", "check_consistency", "review", "commit"],
  "consistency_report": {},
  "review_report": {},
  "checkpoint_id": "..."
}
```

---

## 8. 数据库建议

新增 `chapter_generations` 表：

```sql
CREATE TABLE chapter_generations (
    id UUID PRIMARY KEY,
    story_id UUID NOT NULL REFERENCES stories(id),
    chapter_id UUID NOT NULL REFERENCES chapters(id),
    user_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL,
    request JSONB NOT NULL DEFAULT '{}',
    draft TEXT,
    word_count INT,
    execution_history JSONB NOT NULL DEFAULT '[]',
    consistency_report JSONB,
    review_report JSONB,
    checkpoint_id UUID,
    error_message TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_chapter_generations_chapter
    ON chapter_generations(story_id, chapter_id, created_at DESC);

CREATE INDEX idx_chapter_generations_status
    ON chapter_generations(status);
```

调整 `chapters` 表：

```sql
ALTER TABLE chapters ADD COLUMN last_generation_id UUID NULL;
ALTER TABLE chapters ADD COLUMN content TEXT NULL;
```

如后续正文过大，可把 `draft` 和 `content` 迁移到对象存储，数据库只保留 `content_url` / `draft_url`。

---

## 9. 待产品确认的问题

1. 一次生成完成后，是否默认覆盖 `chapters.content`？
   - 建议 MVP 默认采用成功结果，后续再做人工选择。
2. 同一章节重复生成时，是否保留全部历史版本？
   - 建议保留，避免丢稿，也方便后续版本对比。
3. 章节 ID 是先由业务系统创建，还是生成时自动创建？
   - 建议先创建章节，再生成，保证业务主数据清晰。
4. SSE 最终由 Java 直接提供，还是 Java 只做反向代理？
   - 建议目标由 Java 对外提供；MVP 可先代理 Python SSE。
5. Python 是否允许直接写业务库？
   - 建议目标不允许。过渡期可以短暂保留，但应尽快迁移到 Java 落库。

---

## 10. 下一步开发建议

优先级从高到低：

1. 补齐 `ChapterGeneration` 需求和表设计。详见 [ChapterGeneration 需求与表设计](./chapter-generation-requirements.md)。
2. 明确章节当前正文与历史生成记录的关系。
3. 将前端依赖的业务 API 统一规划到 Java Backend。
4. 保留 Python FastAPI 原型，但新增内部 AI Worker API 形态。
5. 更新开发计划，把“生成历史查询”和“Java 后端接管业务 API”加入 MVP。
