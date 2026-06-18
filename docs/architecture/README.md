# DreamWeaver 架构文档

本目录包含 DreamWeaver 项目的完整架构设计文档（描述**目标架构**）。

> ⚠️ 各能力是否已实现，以 [实现状态总表 STATUS.md](../STATUS.md) 为唯一权威。本目录文档涉及实现进度处均应引用该表。

## 文档列表

### [系统架构设计文档](./system-architecture.md)
完整的系统架构设计，包含：
- 系统概述和核心目标
- 总体架构和分层设计
- Agent 工作流架构
- 核心子系统设计（结构化记忆、上下文压缩、Checkpoint、多模型适配）
- 数据模型设计
- 接口设计（REST API + SSE）
- 部署架构
- 非功能性需求（性能、可用性、安全性）
- 风险评估
- 技术演进路线

### [架构决策记录（ADR）](./adr/)
重要技术决策的文档化记录：

- **[ADR-001: 选择 LangGraph 作为 Agent 编排框架](./adr/ADR-001-langgraph.md)**  
  为什么选择 LangGraph 而不是手动编排、Airflow 或 Temporal

- **[ADR-002: 采用结构化记忆管理长文本上下文](./adr/ADR-002-structured-memory.md)**  
  如何通过结构化记忆实现 40%+ 压缩率，管理 100 万字+小说

- **[ADR-003: 使用 Checkpoint 机制实现任务恢复](./adr/ADR-003-checkpoint.md)**  
  如何保证长时间任务可断点恢复，恢复时间 < 10s

- **[ADR-004: 多模型适配与动态路由策略](./adr/ADR-004-multi-model-routing.md)**  
  如何通过 OpenRouter 接入 100+ 模型，实现成本优化和高可用

## 架构概览

### 系统分层

```
┌─────────────────────────────────────────────┐
│           Frontend Layer                     │
│       React + TypeScript + SSE               │
└───────────────────┬─────────────────────────┘
                    │
┌───────────────────▼─────────────────────────┐
│           API Gateway                        │
│       Nginx / API Gateway                    │
└───────────────────┬─────────────────────────┘
                    │
        ┌───────────┴───────────┐
        │                       │
┌───────▼────────┐    ┌────────▼──────────┐
│  Java Service  │    │  Python AI Service │
│  Spring Boot   │    │  FastAPI+LangGraph │
└───────┬────────┘    └────────┬───────────┘
        │                       │
        └───────────┬───────────┘
                    │
        ┌───────────▼───────────┐
        │     Data Layer        │
        │ PostgreSQL+Redis+OSS  │
        └───────────────────────┘
```

### Agent 工作流

```
load_runtime_context
    ↓
novel_context
    ↓
plan_chapter
    ↓
generate_draft
    ↓
check_consistency
    ↓
review → commit
    ↓
rewrite → review
```

### 四层记忆结构

```
Novel Memory
│
├── Timeline          # 关键事件时间线
├── Character Graph   # 人物状态和关系
├── Foreshadow Memory # 伏笔管理
└── World State       # 世界观状态
```

## 核心技术选型

| 层次 | 技术栈 | 说明 |
|------|--------|------|
| 前端 | React + TypeScript | 创作控制台、实时预览 |
| API 网关 | Nginx | 反向代理、SSL、限流 |
| Java 服务 | Spring Boot | 用户管理、审计日志 |
| Python AI | FastAPI + LangGraph | Agent 工作流引擎 |
| AI 编排 | LangGraph | Multi-Agent 编排 |
| 模型聚合 | OpenAI 兼容接口（目标 OpenRouter） | 目标 100+ 模型；**当前实际仅接入 MiMo 单模型** |
| 数据库 | PostgreSQL | 主数据库 |
| 缓存 | Redis | 会话、状态缓存 |
| 存储 | OSS | 章节内容存储 |
| 向量库 | Chroma | 语义检索 |

## 性能目标

| 指标 | 目标值 | 当前状态 |
|------|--------|----------|
| 上下文压缩率 | 40%+ | 设计中 |
| Checkpoint 恢复时间 | < 10s | 设计中 |
| 查询响应时间 | < 2s | 设计中 |
| API 响应时间 | P95 < 500ms | 设计中 |
| 章节生成时间 | 3000 字 < 2min | 设计中 |
| 并发用户数 | 1000+ | 设计中 |

## 开发阶段

### Phase 1: MVP（2 个月）
- [ ] 核心 Agent 工作流
- [ ] 基础记忆系统
- [ ] 单模型支持（Claude）
- [ ] 基础 Checkpoint

### Phase 2: 优化（1 个月）
- [ ] 多模型接入
- [ ] 上下文压缩优化
- [ ] SSE 流式输出
- [ ] 性能优化

### Phase 3: 增强（2 个月）
- [ ] 小说技能库
- [ ] 高级伏笔管理
- [ ] 人工介入机制
- [ ] 监控告警

## 相关资源

- [实现状态总表 STATUS.md](../STATUS.md) ← 判断"是否已实现"的唯一权威
- [PRD 产品需求文档](../PRD.md)
- [项目主文档](../../.claude/CLAUDE.md)
- [开发 Skills](../../.claude/skills/)
- [项目 README](../../README.md)

## 文档维护

- **负责人**: System Architect
- **更新频率**: 重大架构变更时更新
- **最后更新**: 2026-06-04
