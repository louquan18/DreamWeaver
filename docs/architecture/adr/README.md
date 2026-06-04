# 架构决策记录（ADR）索引

本目录包含 DreamWeaver 项目的所有架构决策记录（Architecture Decision Records）。

## 什么是 ADR？

ADR 是一种记录重要架构决策的文档格式，包含：
- 决策背景和问题陈述
- 备选方案对比分析
- 最终决策和理由
- 决策后果和风险评估

## 决策记录列表

### [ADR-001: 选择 LangGraph 作为 Agent 编排框架](./ADR-001-langgraph.md)
**日期**: 2026-06-04  
**状态**: 已接受  
**摘要**: 选择 LangGraph 作为 Multi-Agent 工作流编排框架，相比手动编排、Airflow、Temporal，LangGraph 提供开箱即用的 Checkpoint、流式输出和状态管理，最适合我们的实时交互场景。

**关键决策**:
- ✅ 使用 LangGraph StateGraph 编排 8+ Agent 节点
- ✅ 采用 TypedDict 定义状态结构
- ✅ 使用 PostgresSaver 持久化 Checkpoint
- ✅ 通过 astream_events 实现流式输出

**影响范围**: Agent 工作流、状态管理、Checkpoint 机制

---

### [ADR-002: 采用结构化记忆管理长文本上下文](./ADR-002-structured-memory.md)
**日期**: 2026-06-04  
**状态**: 已接受  
**摘要**: 采用结构化记忆（Timeline/Character Graph/Foreshadow/World State）+ 向量检索的混合方案，解决长篇小说（100万字+）的上下文窗口限制问题，实现 40%+ 压缩率。

**关键决策**:
- ✅ 四层记忆结构：Timeline、Character Graph、Foreshadow、World State
- ✅ 章节压缩流水线：事件抽取 → 摘要生成 → 结构化存储
- ✅ 混合检索：结构化记忆（精确）+ 向量检索（语义）
- ✅ 目标压缩率 40%+，查询响应 < 2s

**影响范围**: 上下文管理、成本控制、一致性检查

---

### [ADR-003: 使用 Checkpoint 机制实现任务恢复](./ADR-003-checkpoint.md)
**日期**: 2026-06-04  
**状态**: 已接受  
**摘要**: 使用 LangGraph 内置的 Checkpoint 机制（PostgresSaver）实现任务断点恢复，保证长时间任务（2-4分钟）在服务重启、网络中断、模型异常时可无缝恢复，恢复时间 < 10s。

**关键决策**:
- ✅ 使用 LangGraph PostgresSaver 自动保存状态
- ✅ 每个节点执行后自动创建 Checkpoint
- ✅ 通过 thread_id 识别和恢复任务
- ✅ 支持查询历史 Checkpoint

**影响范围**: 任务可靠性、用户体验、成本节省

---

### [ADR-004: 多模型适配与动态路由策略](./ADR-004-multi-model-routing.md)
**日期**: 2026-06-04  
**状态**: 已接受  
**摘要**: 采用 OpenRouter 作为统一的多模型聚合层，支持 100+ 模型（GPT/Claude/Gemini/DeepSeek/Qwen），通过动态路由策略为不同 Agent 选择最优模型，平衡质量和成本。

**关键决策**:
- ✅ 使用 OpenRouter 统一聚合 100+ 模型
- ✅ 统一 OpenAI 格式接口
- ✅ 配置化模型路由（YAML）
- ✅ 自动 Fallback 机制
- ✅ 路由策略：规划用 GPT-4、写作用 Claude、检查用 GPT-3.5

**影响范围**: 成本优化、可用性、灵活性

---

## ADR 状态说明

- **提议中** - 正在讨论，尚未决策
- **已接受** - 已采纳并实施
- **已弃用** - 不再使用
- **已替代** - 被新的 ADR 替代

## 如何编写 ADR

使用 [ADR 模板](../../.claude/skills/system-architect/adr-template.md) 创建新的架构决策记录。

## 决策历史时间线

```
2026-06-04
├── ADR-001: LangGraph 编排框架
├── ADR-002: 结构化记忆系统
├── ADR-003: Checkpoint 恢复机制
└── ADR-004: 多模型路由策略
```

## 相关文档

- [系统架构设计文档](../system-architecture.md)
- [技术栈说明](../../README.md)
- [开发指南](../../CLAUDE.md)
