# Python AI 服务解耦 / 根除双写

**日期**: 2026-06-18
**分支**: `refactor/python-ai-worker-decouple`
**状态**: 代码改动已落地并通过验证（import + configure_mappers + pytest 52 passed）；待本地库 reset 后端到端回归。

## 一句话
把 Python 收敛为"纯 AI Worker",删除其重复的业务 CRUD 与写业务表的 hack，使每张表只有一个服务能写（single writer per table），从结构上消除双写。

## 决策（已确认）
- 共用一个 Postgres。
- 去掉 `story_memories.story_id`（及 `checkpoints` 的 story_id/chapter_id）指向业务表的外键，改为普通索引 UUID。

## 文档
- [plan.md](./plan.md) — 完整方案：为什么会双写 / 为什么改完不会 / 本次妥协 / 后续演进 / 改动清单 / 验证结果。

## 关键妥协（详见 plan.md 第 5 节）
1. alembic 001 被重写为只建 AI 域表 → **本地库需 reset 一次**（`docker compose down -v` 重建）。
2. 跨服务两段写时序偏差（记忆 vs 采用）未解决，MVP 接受。
