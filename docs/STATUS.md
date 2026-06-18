# DreamWeaver 实现状态总表（Single Source of Truth）

**版本**: v1.0
**日期**: 2026-06-17
**用途**: 本表是"文档声称 vs 代码现状"的唯一权威对照表。所有其他文档（PRD、架构、ADR）在涉及"是否已实现"时，应引用本表，而不是各自重复声明。

> ⚠️ 重要原则：本表中的"目标值"是规划指标，**尚无评测脚本支撑**，不得当作已测得的结果。带 `file:line` 的证据均来自当前代码库。

图例：

- ✅ **已实现**：代码中可运行、与文档一致
- 🚧 **部分 / 未验证**：有代码骨架，但未完成、未接线或无评测数据
- ⚠️ **有风险 / 旁路**：实现了，但与文档描述的行为或边界存在偏差
- ❌ **未实现 / 与文档矛盾**：代码中不存在，或与文档画法相反

---

## 1. 工作流与 Agent

| 能力 | 状态 | 说明与证据 |
| --- | --- | --- |
| LangGraph 8 节点工作流 | ✅ | 8 个节点齐全：`backend/python-ai/src/workflows/graph.py:97-142` |
| 工作流末端循环 `rewrite → review` | ✅ | `graph.py:139`；**注意**：架构文档曾画成 `rewrite → END`，以本表与代码为准 |
| 条件路由（一致性/评审分数门限） | ✅ | `graph.py:30-78`（high>0 或 issues≥3 → review；score<75 且 retry<3 → rewrite） |
| "AI 自评审-自修复闭环"对用户可见 | ⚠️ | 流式接口在 draft token 流完成即返回；consistency/review/rewrite/commit 在**后台 fire-and-forget** 执行，用户路径不等待其结果：`backend/python-ai/src/api/routes/chapters.py:122-138` |

## 2. SSE 实时输出（契约权威源 = 代码）

| 项 | 状态 | 说明与证据 |
| --- | --- | --- |
| SSE 事件类型 | ✅（以代码为准） | 实际事件：`token` / `node_start` / `node_end` / `done` / `error`，格式 `event: <type>\ndata: <json>`：`chapters.py:166-168` |
| 节点状态与进度真实反映执行 | ⚠️ | `node_start/node_end` 与进度值（5/15/30/50）是**按固定顺序硬编码发出**，并非由真实节点执行驱动：`chapters.py:58-73`、`122-123` |
| `progress` 独立事件 / percent 到 65/100 | ❌ | 代码无独立 `progress` 事件，PRD 中的 `{"type":"progress","percent":65}` 不存在；进度信息内嵌在 node 事件里 |

> **权威定义**：SSE 事件契约以 `chapters.py` 为唯一权威。PRD 第 9 节、架构文档第 6.2 节的事件示例若与此不符，以本表为准。

## 3. State Schema（契约权威源 = 代码）

| 项 | 状态 | 说明与证据 |
| --- | --- | --- |
| `NovelState` 字段定义 | ✅（以代码为准） | `backend/python-ai/src/workflows/state.py:8-47` |
| `checkpoint_id` 字段 | ❌ | 代码中的 `NovelState` **没有** `checkpoint_id` 字段；PRD 与架构文档的 State 示例列了它，以代码为准 |
| 实际字段 | — | story_id / chapter_id / user_id / novel_context / chapter_outline / generated_draft / consistency_report / review_report / execution_history / current_node / error / retry_count / metadata |

## 4. Checkpoint 恢复

| 能力 | 状态 | 说明与证据 |
| --- | --- | --- |
| 生产级 Checkpoint（PostgresSaver） | ❌ | 实际使用 `MemorySaver()`（内存态，进程重启即丢失）：`graph.py:95`；`backend/python-ai/src/checkpoint/` 仅含空 `__init__.py` |
| "服务重启后可恢复" | ❌ | 与上一行直接矛盾：MemorySaver 无法在重启后恢复，而这正是文档声称要解决的场景 |
| `checkpoints` 表 / model 接线 | 🚧 | `models/checkpoint.py` 存在，但未与工作流 checkpointer 接线 |
| 恢复时间 < 10s | ❌ | 目标值，无评测，且当前根本不支持持久化恢复 |

详见 [ADR-003](./architecture/adr/ADR-003-checkpoint.md) 的"现状更新"小节。

## 5. 多模型路由

| 能力 | 状态 | 说明与证据 |
| --- | --- | --- |
| 按 Agent 选模型 + 温度的机制 | 🚧 | 机制存在：`backend/python-ai/src/models/provider.py:43-84`（get_agent_llm 按 agent_type 映射模型与温度） |
| 多 Provider 动态路由（GPT/Claude/Gemini/DeepSeek/Qwen） | ❌ | 实际六个 Agent 全部配置为 `mimo-7b` 单一模型：`backend/python-ai/src/core/config.py:37-42`；无独立 `router.py`，无按任务切换 |
| 实际接入模型 | ✅ | 小米 MiMo（OpenAI 兼容接口）：`backend/python-ai/src/models/mimo_client.py`、`config.py:32-34` |
| 自动 Fallback | ❌ | 无 fallback 实现 |

详见 [ADR-004](./architecture/adr/ADR-004-multi-model-routing.md) 的"现状更新"小节。

## 6. 结构化记忆与上下文压缩

| 能力 | 状态 | 说明与证据 |
| --- | --- | --- |
| 四层记忆结构（Timeline/Character/Foreshadow/World） | 🚧 | `backend/python-ai/src/memory/`（manager.py / schema.py / compression.py / vector_store.py）存在骨架 |
| 上下文压缩 40%+ | 🚧 | `memory/compression.py` 存在，但**无 benchmark/评测**，40% 无出处。注意 PRD 与架构文档曾给出 40% 与 ≈67% 两个不一致数值 |
| 向量库（Chroma 语义检索） | 🚧 | `memory/vector_store.py` + 配置 `config.py:50-52` 存在；根目录 `docker-compose.yml` 已编排 `chroma` 服务（端口 8100、持久化卷）。注意：架构文档第 7 节的 compose 片段是简化示意，曾遗漏该服务，以根目录实际 compose 为准 |

## 7. 安全

| 能力 | 状态 | 说明与证据 |
| --- | --- | --- |
| 认证（JWT） | ❌ | Java `security/` 仅有空 `package-info.java` |
| 授权（RBAC） | ❌ | 未实现 |
| 审计日志 | ❌ | Java `audit/` 仅有空 `package-info.java` |
| 限流（100 req/min） | ❌ | 未实现 |
| user 体系 | ❌ | `user_id` 当前可空/模拟：`chapters.py:21`、`stories/chapters` 需求文档标注"MVP 可固定或模拟" |

> 架构文档第 8.3 节将上述能力作为设计列出，但当前**均未实现**，请勿据此判断系统已有安全防护。

## 8. 业务后端与服务边界

| 项 | 状态 | 说明与证据 |
| --- | --- | --- |
| Java 为唯一业务后端 | ⚠️ | 目标如此，但当前 **Python 仍持有完整 stories/chapters CRUD + repository**：`backend/python-ai/src/api/routes/stories.py`、`repositories/*`；Java 侧也有同名 entity/repository/service → **存在双写风险** |
| `chapter_generations` 表 | ✅（Java 侧） | Java entity 已存在：`backend/java-service/.../entity/ChapterGeneration.java`；但**架构文档第 5 节数据模型遗漏了该表**（见 [产品需求](./product/chapter-generation-requirements.md)） |
| Java↔Python 内部 API（/internal/ai/...） | 🚧 | 产品文档已定义契约，落地状态以代码为准，尚未确认完整打通 |

## 9. 其他

| 项 | 状态 | 说明与证据 |
| --- | --- | --- |
| 对象存储（OSS）存章节正文 | ❌ | OSS 配置全空：`config.py:44-48`；draft 走 TEXT/内存，`done` 事件 `saved_chapter_id=None`：`chapters.py:129` |
| Skill 知识库 / 语料蒸馏流水线 / 覆盖 20+ 题材 | ❌ | 仓库无任何对应模块或数据；PRD 第 10 节为规划 |
| 性能 P95<500ms / 并发 1000+ | ❌ | 无压测支撑；且对分钟级 LLM 生成接口用 500ms P95 口径不当 |

---

## 文档导航

- [PRD 产品需求文档](./PRD.md)
- [系统架构设计](./architecture/system-architecture.md)
- [架构决策记录 ADR](./architecture/adr/)
- [章节生成需求与表设计](./product/chapter-generation-requirements.md)
- [需求确认与后端边界](./product/requirements-confirmation.md)

## 维护约定

- 任何"已实现/未实现"的判断**只在本表更新**，其他文档引用本表。
- 更新本表时必须附 `file:line` 证据，不得凭印象标注。
- 目标值（压缩率、恢复时间、并发等）在有评测脚本与数据前，一律标注为"目标，未验证"。
