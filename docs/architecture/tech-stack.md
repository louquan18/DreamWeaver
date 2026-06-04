# DreamWeaver 技术选型总结

**版本**: v1.0  
**日期**: 2026-06-04  
**作者**: System Architect

---

## 概述

本文档总结 DreamWeaver 项目的核心技术选型决策，提供快速参考。详细分析请查阅对应的 ADR 文档。

---

## 核心技术栈

### 1. Agent 编排框架：LangGraph ✅

**选型**: LangGraph  
**备选**: 手动编排、Airflow、Temporal  
**决策文档**: [ADR-001](./adr/ADR-001-langgraph.md)

**选择理由**:
- ✅ 内置 Checkpoint 机制（PostgresSaver）
- ✅ 流式输出支持（astream_events）
- ✅ 清晰的状态管理（TypedDict）
- ✅ 可视化工具（draw_mermaid）
- ✅ 轻量级，无需独立部署

**关键特性**:
```python
workflow = StateGraph(NovelState)
workflow.add_node("context", context_agent)
workflow.add_node("planner", planner_agent)
# ...
checkpointer = PostgresSaver(connection_string)
app = workflow.compile(checkpointer=checkpointer)
```

**对比**:
| 方案 | 开发成本 | 维护成本 | 功能完整性 | 推荐度 |
|------|---------|---------|-----------|--------|
| LangGraph | 低 | 低 | 高 | ⭐⭐⭐⭐⭐ |
| 手动编排 | 中 | 高 | 中 | ⭐⭐ |
| Airflow | 高 | 高 | 中 | ⭐⭐ |
| Temporal | 高 | 高 | 高 | ⭐⭐⭐ |

---

### 2. 上下文管理：结构化记忆 + 向量检索 ✅

**选型**: 结构化记忆（Timeline/Character/Foreshadow/World）+ 向量检索  
**备选**: 全文拼接、全文摘要、纯 RAG  
**决策文档**: [ADR-002](./adr/ADR-002-structured-memory.md)

**选择理由**:
- ✅ 压缩率 40%+（3000 字 → 800 字）
- ✅ 针对性检索（人物、伏笔、事件）
- ✅ 一致性检查便捷
- ✅ 可扩展性强

**四层记忆结构**:
```
Timeline          → 关键事件时间线
Character Graph   → 人物状态和关系图
Foreshadow Memory → 伏笔埋设和回收
World State       → 世界观规则和设定
```

**对比**:
| 方案 | 压缩率 | 一致性 | 成本 | 推荐度 |
|------|--------|--------|------|--------|
| 结构化记忆 + 向量 | 40%+ | 高 | 低 | ⭐⭐⭐⭐⭐ |
| 全文拼接 | 0% | 高 | 高 | ⭐ |
| 全文摘要 | 93% | 中 | 中 | ⭐⭐⭐ |
| 纯 RAG | 60% | 中 | 中 | ⭐⭐⭐ |

---

### 3. 断点恢复：LangGraph Checkpoint ✅

**选型**: LangGraph Checkpoint (PostgresSaver)  
**备选**: 无 Checkpoint、Redis 缓存、Temporal  
**决策文档**: [ADR-003](./adr/ADR-003-checkpoint.md)

**选择理由**:
- ✅ 开箱即用（无需额外代码）
- ✅ 状态完整性保证（PostgreSQL 事务）
- ✅ 版本管理（可追溯历史）
- ✅ 恢复速度 < 10s

**使用示例**:
```python
checkpointer = PostgresSaver(connection_string)
app = workflow.compile(checkpointer=checkpointer)

# 执行（自动保存）
config = {"configurable": {"thread_id": "story-123"}}
result = await app.ainvoke(initial_state, config)

# 恢复（不传初始状态）
result = await app.ainvoke(None, config)
```

**对比**:
| 方案 | 实现成本 | 恢复速度 | 可靠性 | 推荐度 |
|------|---------|---------|--------|--------|
| LangGraph Checkpoint | 低 | < 10s | 高 | ⭐⭐⭐⭐⭐ |
| 无 Checkpoint | 低 | N/A | 低 | ⭐ |
| Redis 缓存 | 中 | < 5s | 中 | ⭐⭐⭐ |
| Temporal | 高 | < 10s | 高 | ⭐⭐⭐ |

---

### 4. 多模型接入：OpenRouter ✅

**选型**: OpenRouter  
**备选**: 单一模型、手动适配、自建路由  
**决策文档**: [ADR-004](./adr/ADR-004-multi-model-routing.md)

**选择理由**:
- ✅ 统一 OpenAI 格式接口
- ✅ 支持 100+ 模型（GPT/Claude/Gemini/DeepSeek/Qwen）
- ✅ 自动 Fallback
- ✅ 配置化路由（无需改代码）

**路由策略**:
| Agent | 模型 | 理由 |
|-------|------|------|
| Context | Claude-3.5-Sonnet | 中文理解好 |
| Planner | GPT-4-Turbo | 推理能力强 |
| Writer | Claude-3.5-Sonnet-200k | 长文本窗口 |
| Consistency | GPT-3.5-Turbo | 成本低 |
| Reviewer | Claude-3-Opus | 质量高 |

**对比**:
| 方案 | 灵活性 | 开发成本 | 运行成本 | 推荐度 |
|------|--------|---------|---------|--------|
| OpenRouter | 高 | 低 | 中 | ⭐⭐⭐⭐⭐ |
| 单一模型 | 低 | 低 | 高 | ⭐⭐ |
| 手动适配 | 中 | 高 | 低 | ⭐⭐⭐ |
| 自建路由 | 高 | 高 | 低 | ⭐⭐⭐⭐ |

---

## 完整技术栈

### 后端

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| Python AI 服务 | FastAPI | 0.110+ | 异步 Web 框架 |
| Agent 编排 | LangGraph | 0.2+ | Multi-Agent 工作流 |
| LLM 框架 | LangChain | 0.2+ | LLM 抽象和工具 |
| 模型聚合 | OpenRouter | - | 统一多模型接口 |
| 数据库 ORM | SQLAlchemy | 2.0+ | 异步 ORM |
| 数据迁移 | Alembic | 1.13+ | 数据库版本管理 |
| 向量库 | Chroma | 0.4+ | 语义检索 |
| Java 服务 | Spring Boot | 3.x | 用户管理、审计 |

### 数据层

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 主数据库 | PostgreSQL | 15+ | 关系型数据 |
| 缓存 | Redis | 7+ | 会话、热数据缓存 |
| 对象存储 | OSS/S3 | - | 章节内容存储 |
| 向量存储 | Chroma | 0.4+ | Embedding 存储 |

### 前端

| 组件 | 技术 | 版本 | 用途 |
|------|------|------|------|
| 框架 | React | 18+ | UI 框架 |
| 语言 | TypeScript | 5+ | 类型安全 |
| 构建工具 | Vite | 5+ | 快速构建 |
| 实时通信 | SSE | - | 流式输出 |

### 基础设施

| 组件 | 技术 | 用途 |
|------|------|------|
| 容器化 | Docker | 容器化部署 |
| 编排 | Docker Compose | 本地开发 |
| 反向代理 | Nginx | API 网关、SSL |
| 监控 | Prometheus + Grafana | 指标监控 |
| 日志 | Loguru (Python) | 日志记录 |

---

## 成本估算

### 月度成本（1000 章生成）

| 项目 | 成本 | 说明 |
|------|------|------|
| LLM 调用 | ~$1000 | OpenRouter 模型调用 |
| 数据库 | ~$50 | PostgreSQL 托管服务 |
| 缓存 | ~$20 | Redis 托管服务 |
| 对象存储 | ~$10 | OSS 存储费用 |
| 服务器 | ~$200 | Python + Java 服务 |
| **总计** | **~$1280** | |

### 成本优化策略

1. **模型路由优化** - 简单任务用低成本模型（GPT-3.5）
2. **上下文压缩** - 40%+ 压缩率降低 Token 消耗
3. **缓存策略** - 热数据缓存，减少数据库查询
4. **Checkpoint 复用** - 避免重复调用 LLM

---

## 性能指标

| 指标 | 目标值 | 监控方式 |
|------|--------|---------|
| 上下文压缩率 | 40%+ | 自定义指标 |
| Checkpoint 恢复时间 | < 10s | 业务监控 |
| 查询响应时间 | < 2s | APM |
| API 响应时间 | P95 < 500ms | APM |
| 章节生成时间 | 3000 字 < 2min | 业务监控 |
| 并发用户数 | 1000+ | 压测 |
| 一致性问题修复率 | 80%+ | 业务监控 |

---

## 部署架构

### 开发环境
```
Docker Compose
├── nginx (反向代理)
├── java-service (Spring Boot)
├── python-ai (FastAPI)
├── postgres (数据库)
└── redis (缓存)
```

### 生产环境（云）
```
云负载均衡
    ↓
Kubernetes 集群
├── Ingress (Nginx)
├── Java Service (多副本)
├── Python AI Service (多副本)
├── PostgreSQL (托管服务，主从)
├── Redis (托管服务，集群)
└── OSS (对象存储)
```

---

## 技术风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| LLM API 不稳定 | 高 | 中 | 多模型冗余 + 自动 Fallback |
| LangGraph 版本升级 Breaking Changes | 中 | 中 | 锁定版本 + 定期跟进 |
| 上下文压缩失效 | 中 | 低 | 混合检索 + 人工审核 |
| Checkpoint 损坏 | 高 | 低 | 定期备份 + 主从复制 |
| 成本超预算 | 中 | 中 | 成本监控 + 模型降级 |
| 向量检索召回率不足 | 中 | 中 | 混合检索（向量 + 关键词）|

---

## 技术债务

### 短期债务（3 个月内偿还）

1. **Chroma 迁移** - 当前使用 Chroma，生产环境可能需要 Pinecone/Qdrant
2. **Checkpoint 压缩** - 当前完整状态存储，需要压缩优化
3. **事件抽取优化** - Prompt 需要迭代优化

### 长期债务（6-12 个月）

1. **智能路由** - 当前静态路由，未来实现基于成本/延迟/质量的动态路由
2. **模型微调** - 针对网文场景微调专用模型
3. **分布式 Checkpoint** - 当前单库存储，高并发时可能需要分布式方案

---

## 演进路线图

### Phase 1: MVP（2 个月）
- [x] 技术选型完成
- [ ] 核心 Agent 工作流
- [ ] 基础记忆系统
- [ ] 单模型支持（Claude）
- [ ] 基础 Checkpoint

### Phase 2: 优化（1 个月）
- [ ] 多模型接入（OpenRouter）
- [ ] 上下文压缩优化
- [ ] SSE 流式输出
- [ ] 性能优化

### Phase 3: 增强（2 个月）
- [ ] 小说技能库
- [ ] 高级伏笔管理
- [ ] 人工介入机制
- [ ] 监控告警完善

### Phase 4: 规模化（持续）
- [ ] 分布式架构
- [ ] 模型微调
- [ ] 智能路由
- [ ] 成本优化

---

## 相关文档

- [系统架构设计](./system-architecture.md)
- [ADR 索引](./adr/README.md)
- [PRD 产品需求](../PRD.md)
- [开发指南](../../.claude/CLAUDE.md)

---

## 决策者

- **System Architect**: 技术选型、架构设计
- **AI Team**: Agent 实现、模型调优
- **Backend Team**: 服务实现、数据库设计
- **DevOps Team**: 部署、监控、运维

---

**最后更新**: 2026-06-04
