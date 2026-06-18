# DreamWeaver AI 共创业务设计 v1

**版本**: v1.0  
**日期**: 2026-06-18  
**状态**: 业务设计草案，作为后续开发任务规划依据  
**范围**: 小说创建、章节大纲、正文生成、评审修复、记忆确认、伏笔生命周期  

---

## 1. 产品定位

DreamWeaver 第一版面向想玩 AI 共创的普通用户，优先服务玄幻 / 修仙题材。产品目标不是专业写作软件，而是让用户用较低成本快速得到“能看、能爽、能持续推进”的小说内容。

核心定位：

> Agent 主动担任编剧，持续提出剧情方案、生成正文、维护记忆与伏笔；作者作为总编辑，通过选择、调整、确认来控制作品方向。

### 1.1 目标用户

- 想体验 AI 共创小说的普通用户。
- 有脑洞但不想从零逐字码字的用户。
- 希望快速看到修仙爽文剧情推进的用户。

### 1.2 质量目标

- 能看：情节完整，语言通顺，人物行为基本合理。
- 能爽：有明确冲突、期待感、阶段性反馈和章末钩子。
- 快速产出：每章默认约 2000 字，一次生成整章正文。

### 1.3 第一版题材

第一版只围绕玄幻 / 修仙题材设计。后续题材扩展通过新增或替换题材 Skill 完成，例如悬疑、都市、言情、无限流等。

---

## 2. 用户与 Agent 权限边界

### 2.1 Agent 权限

Agent 默认拥有主动编剧权，可以：

- 根据作者设想生成小说蓝图。
- 主动补全主角、主线、核心冲突和轻量世界观。
- 每章生成 3 个不同方向的中纲方案。
- 根据上下文、主线、记忆和伏笔解释为什么这样安排。
- 在作者上传大纲时进行剧情、冲突、节奏和伏笔优化。
- 生成整章正文。
- 进行一致性检查、质量评审和自动修复。
- 从正文中提取时间线、人物状态、世界观补丁和伏笔变化。
- 提出世界观补丁、支线补丁和伏笔计划。

### 2.2 作者权限

作者是总编辑，拥有最终确认权，可以：

- 确认或调整小说蓝图。
- 选择、混选或否决章节中纲方案。
- 通过提示词要求 Agent 调整方向。
- 上传自己的大纲，由 Agent 优化后执行。
- 在正文确认前要求整章重写或局部重写。
- 查看并确认 Agent 提取的记忆。
- 编辑记忆提取结果。
- 忽略轻微评审问题并确认正文。

### 2.3 硬约束

- 世界观补丁必须经作者确认后才生效。
- 记忆不确认，章节不算完成。
- 正文确认后章节冻结，不再支持修改。
- 第一版不做卷结构。
- 第一版强制按章节顺序创作。
- P0 硬冲突必须修复，P1/P2 问题允许作者忽略。

---

## 3. 小说创建流程

小说创建阶段采用“聊天生成，表单展示”的产品形态。

用户可以只输入一句设想，例如：

```text
我想写一个被宗门背叛的少年靠梦境预知复仇的修仙文。
```

Agent 负责生成轻量小说蓝图，并以结构化表单展示给作者确认或调整。

### 3.1 创建阶段必须生成的内容

创建小说时必须生成：

- 主角。
- 主线。
- 核心冲突。
- 轻量世界观。
- 初始风格与节奏偏好。

### 3.2 小说蓝图字段

建议 `NovelBlueprint` 至少包含：

| 字段 | 说明 |
| --- | --- |
| `premise` | 一句话故事设想 |
| `genre` | 题材，第一版默认为玄幻 / 修仙 |
| `tone` | 风格，例如爽文、热血、黑暗、轻松 |
| `protagonist` | 主角初始设定 |
| `main_thread` | 主线目标 |
| `core_conflict` | 核心矛盾 |
| `world_seed` | 轻量世界观种子 |
| `writing_preferences` | 文风、节奏、禁忌和偏好 |
| `locked_facts` | 作者明确锁定、后续不可违反的设定 |

### 3.3 世界观补丁

小说背景允许后续不断打补丁，但不能与已确认设定冲突。

世界观补丁流程：

```text
Agent 提出补丁
  -> 进入 pending
  -> 作者确认或编辑
  -> 写入正式世界观记忆
  -> 成为后续生成硬约束
```

未确认补丁不能作为后续生成的硬约束。

---

## 4. 章节创作流程

章节是第一版核心创作单元。系统不做卷结构，Agent 在每章开始时进行规划。

### 4.1 顺序创作约束

第一版强制按章节顺序创作：

- 上一章未完成正文确认和记忆确认时，不能进入下一章正式生成。
- 这样可以保证时间线、人物状态、伏笔和世界观补丁按顺序沉淀。

### 4.2 标准流程

```text
创建章节草稿
  -> Agent 加载小说蓝图、主线、历史章节、记忆、伏笔
  -> Agent 生成 3 个中纲方案
  -> 作者选择 / 混选 / 调整 / 否决
  -> 作者确认中纲
  -> Agent 一次性生成约 2000 字正文
  -> Agent 进行一致性检查和质量评审
  -> Agent 自动修复硬冲突
  -> 作者确认正文
  -> Agent 提取记忆
  -> 作者确认或编辑记忆
  -> 章节完成并冻结
```

### 4.3 作者上传大纲

作者可以直接上传或输入自己的章节大纲。

默认模式为“Agent 可优化”：

- 保留作者核心意图。
- 优化冲突、节奏、伏笔和章末钩子。
- 如果优化会改变关键剧情，必须在方案里说明原因。

后续可扩展“严格照写”模式，但不作为第一版默认行为。

---

## 5. 三方案中纲机制

每章正文生成前，Agent 必须先提供 3 个中纲方案。

### 5.1 三种方案

| 方案 | 定位 | 目标 |
| --- | --- | --- |
| A 稳健推进 | 推进主线和人物目标 | 保持连贯，降低剧情突兀感 |
| B 强冲突 | 制造高压对抗或意外转折 | 提升爽点、张力和阅读期待 |
| C 伏笔回收 | 优先处理伏笔 | 回收、强化或埋设伏笔 |

### 5.2 C 方案兜底规则

C 方案按以下优先级生成：

```text
优先回收已有伏笔
如果无可回收伏笔，则强化已有伏笔
如果无可强化伏笔，则埋设新伏笔
```

禁止为了“回收伏笔”伪造不存在的前文。

### 5.3 混选机制

作者可以通过提示词混选方案，例如：

```text
采用 B 的冲突强度，但保留 C 的结尾伏笔，不要让反派太早暴露。
```

Agent 应基于作者提示生成最终中纲，而不是机械拼接。

### 5.4 中纲标准格式

章节中纲建议包含：

| 字段 | 说明 |
| --- | --- |
| `title_candidates` | 章节标题候选 |
| `chapter_goal` | 本章目标 |
| `story_summary` | 本章剧情摘要 |
| `scene_outline` | 3-5 个场景的中纲 |
| `characters_involved` | 出场人物与动机 |
| `conflict` | 本章主要冲突 |
| `highlight_moment` | 本章爽点或情绪爆点 |
| `foreshadow_actions` | 伏笔埋设、强化、触发或回收 |
| `memory_references` | 引用的历史记忆和上下文 |
| `why_this_plan` | 为什么这么安排 |
| `ending_hook` | 章末钩子 |
| `risk_notes` | 风险提示，例如提前暴露反派、节奏过快 |

正文生成必须遵守已确认中纲，但允许在不改变关键剧情的前提下补充细节。

---

## 6. 正文生成与评审修复

### 6.1 正文生成

- 默认一次生成整章。
- 目标字数约 2000 字。
- 生成依据包括小说蓝图、已确认中纲、历史章节、记忆、伏笔、作者额外提示词。
- 生成结果在正文确认前可以重写或局部重写。

### 6.2 评审维度

正文生成后，Agent 默认进行评审：

- 设定一致性。
- 人物行为一致性。
- 时间线一致性。
- 主线推进。
- 伏笔使用。
- 节奏与爽点。
- 语言质量。
- 章末钩子。

### 6.3 问题分级

| 级别 | 类型 | 处理规则 |
| --- | --- | --- |
| P0 | 硬冲突 | 必须修复后才能确认 |
| P1 | 明显质量或逻辑问题 | 建议修复，作者可忽略 |
| P2 | 风格、节奏、表达优化 | 提示作者，作者可忽略 |

P0 示例：

- 已确认世界规则为“筑基不能御空飞行”，正文却写筑基主角御空飞行。
- 已确认某角色死亡，正文无解释地让其正常出场。
- 已确认主角不杀无辜，正文无动机地写主角滥杀无辜。

### 6.4 自动修复

Agent 发现 P0 后应自动进入修复流：

```text
检测冲突
  -> 定位冲突段落
  -> 判断修复方式
  -> 局部重写或整章重写
  -> 再次检查
  -> 输出修复说明
```

如果修复需要新增世界观补丁，该补丁必须进入待确认状态，不能直接写入正式世界观。

---

## 7. 记忆提取与确认

章节正文确认后，Agent 必须从正文中提取记忆。作者确认记忆后，章节才算完成。

### 7.1 第一版记忆类型

第一版至少保留：

| 类型 | 说明 |
| --- | --- |
| `TimelineMemory` | 已发生事件 |
| `CharacterMemory` | 人物状态和关系变化 |
| `WorldMemory` | 世界观补丁和已确认规则 |
| `ForeshadowMemory` | 伏笔计划与生命周期 |

可后续增强：

- `MainThreadMemory`：主线进展。
- `AuthorPreference`：作者风格偏好。

### 7.2 记忆确认流程

```text
正文确认
  -> Agent 提取记忆
  -> 展示待确认记忆
  -> 作者编辑 / 删除 / 补充
  -> 作者确认
  -> 写入长期记忆
  -> 章节完成并冻结
```

### 7.3 章节完成条件

章节完成必须同时满足：

- 正文已确认。
- 记忆提取已确认。
- 不存在未修复的 P0 硬冲突。

如果仅存在 P1/P2 问题，作者可以忽略并确认。

---

## 8. 伏笔生命周期

伏笔需要显式建模，并支持生命周期管理。

### 8.1 状态定义

| 状态 | 说明 |
| --- | --- |
| `planned` | 计划埋设，尚未进入正文 |
| `planted` | 已在正文中出现 |
| `reinforced` | 已被强化或多次提示 |
| `triggered` | 已触发，但尚未完全揭示 |
| `revealed` | 已揭示含义 |
| `resolved` | 已完成回收 |
| `abandoned` | 已废弃 |

### 8.2 状态流转

```text
planned -> planted -> reinforced -> triggered -> revealed -> resolved
planned -> abandoned
planted -> abandoned
reinforced -> abandoned
```

Agent 可以提出废弃伏笔，但必须由作者确认。

### 8.3 伏笔绑定对象

伏笔可以绑定：

- 人物。
- 道具。
- 地点。
- 势力。
- 世界规则。
- 主线或支线。

---

## 9. 章节状态机

第一版对外只暴露两个章节主状态。

| 状态 | 说明 |
| --- | --- |
| `DRAFT` | 草稿中，允许生成大纲、调整正文、重写、记忆待确认 |
| `CONFIRMED` | 正文和记忆已确认，章节冻结，不再修改 |

内部任务状态可以更细，但不作为章节主状态暴露。

建议内部流程状态：

```text
outline_options_generating
outline_options_generated
outline_confirmed
draft_generating
draft_generated
reviewing
revision_required
draft_confirmed
memory_extracting
memory_pending_confirm
memory_confirmed
```

### 9.1 状态规则

- 新章节默认进入 `DRAFT`。
- `DRAFT` 阶段允许重新生成大纲、整章重写、局部重写、编辑记忆。
- `CONFIRMED` 阶段禁止修改正文和记忆。
- `CONFIRMED` 后才允许创建下一章并进入正式创作流程。

---

## 10. Agent 工作流设计

### 10.1 小说创建工作流

```text
collect_user_idea
  -> generate_light_blueprint
  -> validate_blueprint
  -> present_blueprint_form
  -> user_confirm_blueprint
  -> save_novel_profile
```

### 10.2 章节大纲工作流

```text
load_runtime_context
  -> load_novel_blueprint
  -> load_story_memory
  -> load_foreshadow_memory
  -> generate_outline_options
  -> explain_outline_options
  -> wait_user_selection_or_feedback
  -> refine_selected_outline
  -> confirm_outline
```

### 10.3 正文生成工作流

```text
load_confirmed_outline
  -> generate_draft
  -> check_consistency
  -> review_quality
  -> rewrite_if_required
  -> present_draft
  -> wait_user_confirmation
```

### 10.4 记忆更新工作流

```text
extract_memory_from_confirmed_draft
  -> detect_memory_conflicts
  -> present_memory_changes
  -> wait_user_confirmation
  -> save_confirmed_memory
  -> freeze_chapter
```

---

## 11. 核心领域对象草案

### 11.1 `NovelBlueprint`

小说蓝图。由创建阶段生成，后续可通过确认过的补丁扩展。

核心字段：

- `id`
- `story_id`
- `premise`
- `genre`
- `tone`
- `protagonist`
- `main_thread`
- `core_conflict`
- `world_seed`
- `writing_preferences`
- `locked_facts`
- `created_at`
- `updated_at`

### 11.2 `ChapterOutlineOption`

章节中纲候选方案。

核心字段：

- `id`
- `story_id`
- `chapter_id`
- `option_type`: `steady` / `conflict` / `foreshadow`
- `title_candidates`
- `chapter_goal`
- `story_summary`
- `scene_outline`
- `characters_involved`
- `conflict`
- `highlight_moment`
- `foreshadow_actions`
- `memory_references`
- `why_this_plan`
- `ending_hook`
- `risk_notes`
- `created_at`

### 11.3 `ChapterOutline`

作者选择和调整后的最终中纲。

核心字段：

- `id`
- `story_id`
- `chapter_id`
- `source_option_ids`
- `user_feedback`
- `final_outline`
- `confirmed_at`

### 11.4 `ChapterDraft`

正文草稿。可以复用现有 `ChapterGeneration`，但语义上应区分“任务记录”和“最终章节正文”。

核心字段：

- `id`
- `story_id`
- `chapter_id`
- `outline_id`
- `content`
- `word_count`
- `review_report`
- `consistency_report`
- `status`
- `created_at`

### 11.5 `MemoryChangeSet`

一次章节确认后待写入的记忆变更集合。

核心字段：

- `id`
- `story_id`
- `chapter_id`
- `source_draft_id`
- `timeline_changes`
- `character_changes`
- `world_changes`
- `foreshadow_changes`
- `status`: `pending` / `confirmed` / `rejected`
- `confirmed_at`

### 11.6 `Foreshadow`

伏笔对象。

核心字段：

- `id`
- `story_id`
- `title`
- `description`
- `status`
- `related_characters`
- `related_items`
- `related_locations`
- `related_world_rules`
- `planned_payoff_hint`
- `created_chapter_id`
- `updated_chapter_id`
- `resolved_chapter_id`

---

## 12. MVP 改造范围

第一版改造聚焦四条闭环。

### 12.1 小说创建改造

目标：

- 从“一般创建小说”升级为“聊天生成轻量小说蓝图”。
- 必须生成主角、主线、核心冲突和轻量世界观。
- 蓝图以表单方式展示并允许作者调整。

### 12.2 章节生成改造

目标：

- 从“创建章节后直接生成正文”升级为“先生成三种中纲方案”。
- 支持作者选择、混选、提示词调整。
- 中纲确认后再生成正文。

### 12.3 评审修复改造

目标：

- 正文生成后自动进行一致性检查和质量评审。
- P0 必须自动修复。
- P1/P2 可展示给作者，由作者决定是否忽略。

### 12.4 记忆确认改造

目标：

- 正文确认后自动提取记忆。
- 记忆展示给作者确认和编辑。
- 记忆确认后章节才进入 `CONFIRMED`。

---

## 13. 非目标范围

第一版不做：

- 卷 / 篇章结构。
- 多人协作。
- 发布、订阅、付费阅读等小说平台能力。
- 正文确认后的修改和重算。
- 复杂支线管理。
- 多题材通用化。
- 富文本编辑器。
- 复杂版本 diff。

---

## 14. 后续扩展点

### 14.1 Skill 扩展

可逐步增加：

- 修仙爽文节奏 Skill。
- 伏笔设计 Skill。
- 人物关系推进 Skill。
- 战斗场景 Skill。
- 悬疑题材 Skill。
- 言情互动 Skill。

Skill 可以同时影响：

- 大纲生成。
- 正文生成。
- 质量评审。
- 记忆提取。

### 14.2 支线与长期规划

第一版不做卷结构，但后续可以增强：

- 主线显式追踪。
- 支线补丁。
- 阶段目标。
- 每 10 章滚动规划。
- 长期伏笔回收计划。

### 14.3 章节冻结后的修订

第一版正文确认后不可修改。后续如果要支持修改，需要设计：

- 章节修订版本。
- 后续章节影响分析。
- 记忆重算。
- 伏笔状态回滚。
- 时间线冲突修复。

---

## 15. 已确认决策清单

| 决策 | 结论 |
| --- | --- |
| 目标用户 | 想玩 AI 共创的普通用户 |
| 质量目标 | 能看、能爽、快速产出 |
| 第一版题材 | 玄幻 / 修仙 |
| Agent 权限 | 主动编剧，可以脑洞大开 |
| 作者角色 | 总编辑，负责选择、调整、确认 |
| 小说创建 | 聊天生成，表单展示 |
| 创建阶段规划 | 不做章节规划 |
| 创建阶段必须生成 | 主角、主线、核心冲突 |
| 世界观 | 轻量起步，后续补丁扩展 |
| 世界观补丁 | 作者确认后才生效 |
| 小说结构 | 只做章，不做卷 |
| 章节方案 | A 稳健推进、B 强冲突、C 伏笔回收 |
| 方案混选 | 允许，通过作者提示词实现 |
| 作者大纲 | Agent 默认可优化 |
| 中纲确认 | 必须确认后才能生成正文 |
| 正文生成 | 一次生成整章 |
| 默认字数 | 约 2000 字 |
| 记忆更新 | Agent 总结，作者确认 |
| 记忆编辑 | 作者可以调整提取结果 |
| 记忆确认 | 不确认则章节不算完成 |
| 伏笔生命周期 | 必须支持 |
| 冲突处理 | P0 自动修复，P1/P2 可忽略 |
| 章节状态 | `DRAFT` / `CONFIRMED` |
| 正文确认后 | 不支持修改 |
| 第一版卷结构 | 不做 |
