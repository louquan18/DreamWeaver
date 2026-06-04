# DreamWeaver - Multi-Agent 长篇小说创作系统

## 项目概述

**DreamWeaver（织梦者）** 是一套面向长篇网络小说创作场景的 Multi-Agent AI 写作系统。

### 核心特性
- 🤖 基于 LangGraph 构建的 Agent 工作流
- 📚 结构化记忆与上下文压缩（40%+ 压缩率）
- 🔄 生产级 Checkpoint 恢复机制（<10s 恢复时间）
- 🎯 多模型动态路由（GPT/Claude/Gemini/DeepSeek/Qwen）
- 📡 SSE 实时流式输出
- ✅ AI 自评审、自修复闭环

### 系统架构
```
Frontend (React + SSE)
    ↓
API Gateway
    ↓
Java Service (Spring Boot) + Python AI Service (LangGraph)
    ↓
PostgreSQL + Redis + Object Storage
```

### 主要解决的问题
1. **长文本上下文窗口限制** - 通过结构化记忆和上下文压缩
2. **长篇创作情节一致性** - 通过多层记忆结构（Timeline/Character Graph/Foreshadow/World State）
3. **人物设定漂移** - 通过 Consistency Agent 检测和 Rewrite Agent 修复
4. **多 Agent 协作** - 通过 LangGraph 状态机编排
5. **任务中断恢复** - 通过 Checkpoint 机制

---

## 技术栈

### 后端
- **Python**: FastAPI + LangGraph + LangChain
- **Java**: Spring Boot (用户管理、审计日志)
- **数据库**: PostgreSQL (主库) + Redis (缓存)
- **存储**: Object Storage (章节存储)

### AI/LLM
- **编排框架**: LangGraph
- **模型聚合**: OpenRouter
- **支持模型**: GPT/Claude/Gemini/DeepSeek/Qwen 系列

### 前端
- **框架**: React
- **实时通信**: SSE (Server-Sent Events)

---

## Agent 工作流

### 核心 Agents
1. **Context Agent** - 历史章节检索、人物状态提取、世界观加载、时间线构建
2. **Planner Agent** - 章节规划、冲突设计、剧情推进
3. **Writer Agent** - 根据规划生成章节草稿（流式输出）
4. **Consistency Agent** - 检测人物/世界观/情节一致性
5. **Reviewer Agent** - 评审语言质量、节奏控制、冲突强度
6. **Rewrite Agent** - 根据评审结果问题定位、局部修复、重写优化

### 工作流节点
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

---

## 目录结构

```
DreamWeaver/
├── backend/
│   ├── python-ai/          # Python AI 服务（LangGraph）
│   └── java-service/       # Java 业务服务（Spring Boot）
├── frontend/               # React 前端
├── docs/                   # 项目文档
└── .claude/
    ├── CLAUDE.md           # 本文件
    ├── skills/             # 开发阶段技能库
    └── memory/             # 项目记忆库
```

---

## 开发指南

### 使用 Claude Skills

项目已配置多个专业 skills，对应不同开发阶段：

- `/system-architect` - 系统架构设计（架构文档、ADR 决策记录）
- `/project-planner` - 项目规划管理（里程碑、Issue 管理）
- `/python-backend` - Python 后端开发（FastAPI、Repository 模式）
- `/langgraph-architect` - LangGraph 工作流设计（State Schema、Workflow、Checkpoint）
- `/context-engineer` - 上下文工程（Memory Schema、Timeline、Compression）
- `/novel-skill-engineer` - 小说技能工程（题材分析、伏笔设计、人物关系图）
- `/test-engineer` - 测试工程（单元测试、集成测试）
- `/reviewer` - 代码审查（Review Checklist）
- `/refactor-engineer` - 重构工程（Refactor Checklist）

### 开发流程建议

#### 阶段 1: 架构设计
```bash
# 使用 system-architect skill
/system-architect
```
- 完成系统架构文档
- 编写架构决策记录（ADR）
- 确定技术选型

#### 阶段 2: 项目规划
```bash
# 使用 project-planner skill
/project-planner
```
- 分解开发里程碑
- 创建 Issues 和任务清单
- 制定开发计划

#### 阶段 3: LangGraph 工作流开发
```bash
# 使用 langgraph-architect skill
/langgraph-architect
```
- 设计 State Schema
- 实现 Workflow 节点
- 配置 Checkpoint 机制

#### 阶段 4: 上下文管理开发
```bash
# 使用 context-engineer skill
/context-engineer
```
- 设计 Memory Schema（Timeline/Character Graph/Foreshadow/World State）
- 实现上下文压缩算法
- 构建时间线管理

#### 阶段 5: 小说技能库开发
```bash
# 使用 novel-skill-engineer skill
/novel-skill-engineer
```
- 题材分析体系
- 伏笔设计机制
- 人物关系图构建

#### 阶段 6: Python 后端开发
```bash
# 使用 python-backend skill
/python-backend
```
- FastAPI 路由实现
- Repository 模式数据访问
- 业务逻辑封装

#### 阶段 7: 测试与审查
```bash
# 使用 test-engineer 和 reviewer skills
/test-engineer
/reviewer
```
- 编写单元测试和集成测试
- 代码审查和质量检查

#### 阶段 8: 重构优化
```bash
# 使用 refactor-engineer skill
/refactor-engineer
```
- 代码重构
- 性能优化
- 技术债务清理

---

## 性能目标

| 指标 | 目标值 |
|------|--------|
| 上下文压缩率 | 40%+ |
| Checkpoint 恢复时间 | <10s |
| 状态完整性 | 100% |
| 覆盖题材 | 20+ |
| 一致性问题修复率 | 80%+ |
| Agent 节点数 | 8+ |

---

## 注意事项

### LangGraph 开发
- 所有 Agent 状态必须通过 `NovelState` TypedDict 定义
- 使用 `checkpointer` 持久化关键节点状态
- 流式输出通过 `astream_events` 实现
- 节点之间通过 `edges` 定义转换条件

### 上下文管理
- 优先使用结构化记忆而非全文本拼接
- Timeline 记录关键事件，避免冗余
- Character Graph 实时更新人物状态
- Foreshadow Memory 追踪伏笔的埋设和回收

### 模型选择
- **规划任务**: 使用推理能力强的模型（Claude/GPT-4）
- **写作任务**: 使用长文本模型（Claude-100k/GPT-4-32k）
- **校验任务**: 使用低成本模型（GPT-3.5/Haiku）
- **评审任务**: 使用高质量模型（Opus/GPT-4）

### 错误处理
- 所有 LLM 调用必须包含重试机制
- Checkpoint 定期保存，异常时自动恢复
- SSE 连接断开时支持重连和续传

---

## 相关文档

- [PRD - 产品需求文档](../docs/PRD.md)
- [架构设计](../docs/architecture/) - 待创建
- [API 文档](../docs/api/) - 待创建
- [开发指南](../docs/development/) - 待创建

---

## 联系方式

- **项目负责人**: louquan
- **项目状态**: 开发中
- **最后更新**: 2026-06-03
