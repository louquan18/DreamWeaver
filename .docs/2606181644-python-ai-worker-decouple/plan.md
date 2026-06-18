# 重构方案：Python AI 服务收敛为纯 AI Worker，根除双写

**状态**: 已落地（代码） · 待本地库 reset 后端到端回归
**分支**: `refactor/python-ai-worker-decouple`
**定位前提**: 学习/演示 MVP，本地一个 Postgres 跑通

---

## 1. 目标
每张表只有一个服务能写（single writer per table），从结构上消除双写，而非靠纪律回避。

## 2. 为什么会双写（改造前）
业务表被 Python 和 Java 同时写，且各自独立建表、独立事务：

- **`stories`**：Java `StoryService.create`（`gen_random_uuid()`）；Python `create_story`（`api/routes/stories.py`）；Python `_ensure_story_exists`（`memory/manager.py`，非法 UUID 时 `uuid.uuid5()` 推导 id，规则与 Java 不同 → 可能建"影子 story"）。
- **`chapters`**：生成链路只 Java 写；但 Python `POST /{story_id}/chapters` 也能建 → 章节号冲突、内容分叉。
- **schema 双管**：Java Flyway `V1` 与 Python Alembic `001/002` 都建 stories/chapters → 同库迁移冲突。

## 3. 为什么改完不会双写（改造后）
| 表 | 唯一写入方 |
|---|---|
| stories / chapters / chapter_generations | 只有 Java（Flyway 建表） |
| story_memories / checkpoints | 只有 Python（alembic 建表，无外键） |

集成模型 = 数据域切分（方案 A）：保留唯一一条跨服务调用（Java→Python 生成，draft 经 SSE `done` 回传），**不新增 Python→Java 调用，不用 CLI**。表集合不再重叠、AI 表不外键到业务表 → 表级双写在结构上不可能发生。

## 4. 改动清单（已执行）
**删除**：`api/routes/stories.py`、`repositories/story_repository.py`、`repositories/chapter_repository.py`、`schemas/`（整目录）、`models/chapter.py`、`models/story.py`、`tests/test_schemas.py`、`alembic/versions/002_add_chapter_content.py`。

**编辑**：
- `api/main.py` — 移除 stories 路由注册。
- `repositories/__init__.py` — 只留 `MemoryRepository`。
- `models/__init__.py` — 只留 `BaseModel / StoryMemory / Checkpoint`。
- `models/story_memory.py` — `story_id` 去外键改普通索引 UUID，移除 `story` 关联。
- `models/checkpoint.py` — `story_id`/`chapter_id` 去外键改普通 UUID，移除 `story` 关联。
- `memory/manager.py` — 删除 `_ensure_story_exists` 及其调用。
- `alembic/env.py` — 只导入 `StoryMemory, Checkpoint`。
- `alembic/versions/001_initial_schema.py` — 重写为只建 `story_memories` + `checkpoints`（无外键）。
- `tests/test_models.py` — 删除 Story/Chapter 用例。

**保留（AI 功能）**：`api/routes/chapters.py`（生成端点）、`health.py`、`workflows/*`、`agents/*`、`memory/*`、`models/{story_memory,checkpoint,base}.py`、`models/provider.py`、`mimo_client.py`、`repositories/memory_repository.py`。

## 5. 本次妥协（MVP，明说）
1. **跨服务两段写偏差**：`commit_node` 先写 `story_memories`，再发 `done` 让 Java 落业务。若 `done` 前 SSE 断开，Java 判失败不采用，但记忆已写 → "记忆有、业务未采用"。域切分不解决，MVP 接受。
2. **去外键后 DB 不强约束记忆归属**：靠应用层保证 `story_id` 来自 Java。
3. **无跨服务事务/补偿**：失败后记忆不自动回滚。
4. **共享库**：逻辑靠"表所有权"隔离，非物理隔离。
5. **alembic 001 被重写** → 本地库需 reset 一次（`docker compose down -v`）。

## 6. 后续演进（触发条件 → 动作）
- 出现"记忆领先业务"bug → 把记忆持久化挪到 Java 确认 adopt 之后（Java 回调 Python）。
- Python 真需读业务数据 → Java 暴露 `/internal/...` 只读 HTTP，httpx 调用（方案 B）；不用 CLI。
- 要独立部署/扩缩 → 升级为分库，AI 数据完全独立。
- 需要强一致 → outbox / saga 补偿。
- checkpoint 真持久化（ADR-003）→ `MemorySaver`→`PostgresSaver`，`checkpoints` 正式由 Python 写。

## 7. 验证结果
- `from src.api.main import app` + `configure_mappers()` → **OK**（无悬空关联）。
- 路由表确认 `/api/stories` 已下线，仅剩 `/api/ai/chapters/*` + `/health`。
- `pytest -q` → **52 passed**。
- 全库静态检查：无任何对已删模块的残留 import。
- ⏳ 待本地库 reset 后跑端到端生成回归（Java create→events→done→落库→adopt）。

## 8. 风险与回滚
- 改动在独立分支 `refactor/python-ai-worker-decouple`；出问题 `git checkout main` 即可。
- 最大风险点（移除关联导致 mapper 报错）已被 `configure_mappers()` 验证排除。
