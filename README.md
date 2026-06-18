# DreamWeaver（织梦者）

> 基于 LangGraph 的 Multi-Agent 长篇小说创作系统

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-green.svg)](https://fastapi.tiangolo.com/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-orange.svg)](https://langchain-ai.github.io/langgraph/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](./LICENSE)

---

## 项目简介

**DreamWeaver（织梦者）** 是一套面向长篇网络小说创作场景的 Multi-Agent AI 写作系统。通过 LangGraph 编排多个专业 Agent，实现从世界观构建到章节生成的完整创作闭环。

### 核心特性

- 🤖 **Multi-Agent 协作** - 基于 LangGraph 的 8+ Agent 工作流
- 📚 **结构化记忆** - Timeline/Character Graph/Foreshadow/World State 四层记忆，40%+ 压缩率
- 🔄 **断点恢复** - 生产级 Checkpoint 机制，恢复时间 < 10s
- 🎯 **多模型路由** - 支持 GPT/Claude/Gemini/DeepSeek/Qwen，智能选择最优模型
- 📡 **实时流式输出** - SSE 推送，Token 级实时显示
- ✅ **自评审闭环** - AI 自动检测一致性问题并修复

---

## 系统架构

```
Frontend (React + SSE)
    ↓
API Gateway (Nginx)
    ↓
Java Service (Spring Boot) + Python AI Service (FastAPI + LangGraph)
    ↓
PostgreSQL + Redis + Object Storage
```

### Agent 工作流

```
load_runtime_context
    ↓
novel_context (加载历史上下文)
    ↓
plan_chapter (规划章节)
    ↓
generate_draft (生成草稿)
    ↓
check_consistency (一致性检查)
    ↓
review → commit (评审 → 提交)
    ↓
rewrite → review (重写 → 再评审)
```

---

## 技术栈

### 后端

| 组件 | 技术 |
|------|------|
| Python AI 服务 | FastAPI + LangGraph + LangChain |
| Java 业务服务 | Spring Boot 3.x |
| Agent 编排 | LangGraph |
| 模型聚合 | OpenRouter (100+ 模型) |
| 数据库 | PostgreSQL 15+ |
| 缓存 | Redis 7+ |
| 对象存储 | OSS / S3 |
| 向量库 | Chroma |

### 前端

| 组件 | 技术 |
|------|------|
| 框架 | React 18+ |
| 语言 | TypeScript |
| 构建 | Vite |
| 实时通信 | SSE (Server-Sent Events) |

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js 18+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose（可选）

### 本地开发

#### 1. 克隆项目

```bash
git clone https://github.com/yourusername/DreamWeaver.git
cd DreamWeaver
```

#### 2. 一键启动（Docker Compose）

```bash
# 配置环境变量
cp backend/python-ai/.env.example backend/python-ai/.env
# 编辑 .env，填入 OPENROUTER_API_KEY

# 启动所有服务
docker compose up -d
```

访问:
- AI 服务 API: http://localhost:8000
- Swagger 文档: http://localhost:8000/docs
- Health Check: http://localhost:8000/health

#### 3. 本地开发 Python AI 服务

```bash
cd backend/python-ai

# 安装 uv（如未安装）
pip install uv

# 创建虚拟环境并安装依赖
uv venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"

# 配置环境变量
cp .env.example .env
# 编辑 .env，填入 OPENROUTER_API_KEY

# 启动基础设施
docker compose up -d postgres redis

# 启动服务（热重载）
uvicorn src.api.main:app --reload --port 8000
```

#### 4. 运行测试

```bash
cd backend/python-ai
pytest -v
```

---

## 项目结构

```
DreamWeaver/
├── backend/
│   ├── python-ai/              # Python AI 服务
│   │   ├── src/
│   │   │   ├── api/            # FastAPI 路由
│   │   │   ├── agents/         # Agent 实现
│   │   │   ├── workflows/      # LangGraph 工作流
│   │   │   ├── memory/         # 记忆系统
│   │   │   ├── models/         # 模型层
│   │   │   └── core/           # 核心配置
│   │   ├── pyproject.toml
│   │   ├── tests/
│   │   └── Dockerfile
│   └── java-service/           # Java 业务服务
│       ├── src/main/java/
│       ├── pom.xml
│       └── Dockerfile
├── frontend/                   # React 前端
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── docker/                     # Docker 配置
│   ├── nginx/                  # Nginx 配置
│   └── postgres/               # PostgreSQL 初始化
├── docs/                       # 项目文档
│   ├── PRD.md                  # 产品需求文档
│   └── architecture/           # 架构设计文档
│       ├── system-architecture.md
│       ├── tech-stack.md
│       └── adr/                # 架构决策记录
├── .claude/                    # Claude 开发配置
│   ├── CLAUDE.md               # Claude 项目说明
│   ├── skills/                 # 开发技能库
│   └── memory/                 # 项目记忆
├── docker-compose.yml
├── README.md
└── LICENSE
```

---

## 核心功能

### 1. 结构化记忆系统

**四层记忆结构**，解决长篇小说（100 万字+）的上下文窗口限制：

- **Timeline**: 关键事件时间线
- **Character Graph**: 人物状态和关系图
- **Foreshadow Memory**: 伏笔埋设和回收
- **World State**: 世界观规则和设定

**压缩率**: 40%+（3000 字 → ~1000 字结构化数据）

### 2. Multi-Agent 协作

**6 个核心 Agent**：

| Agent | 职责 | 模型 |
|-------|------|------|
| Context Agent | 加载历史上下文 | Claude-3.5-Sonnet |
| Planner Agent | 规划章节大纲 | GPT-4-Turbo |
| Writer Agent | 生成章节内容 | Claude-3.5-Sonnet-200k |
| Consistency Agent | 检测一致性问题 | GPT-3.5-Turbo |
| Reviewer Agent | 评审语言质量 | Claude-3-Opus |
| Rewrite Agent | 修复问题段落 | Claude-3.5-Sonnet |

### 3. Checkpoint 断点恢复

- 每个 Agent 节点执行后自动保存状态
- 服务重启/网络中断后可无缝恢复
- 恢复时间 < 10s
- 支持查询历史 Checkpoint

### 4. 多模型动态路由

- 支持 100+ 模型（OpenRouter 聚合）
- 根据任务类型智能选择模型
- 自动 Fallback（主模型不可用时切换备用）
- 成本优化（简单任务用低成本模型）

---

## API 文档

### 章节生成（流式）

```bash
curl -N -H "Accept: text/event-stream" \
  "http://localhost:8000/api/ai/chapters/generate-stream?story_id=story-123&chapter_id=chapter-456"
```

**SSE 事件**:
```
event: token
data: {"content": "第"}

event: node_start
data: {"node": "generate_draft"}

event: progress
data: {"percent": 65}

event: done
data: {"chapter_id": "chapter-456", "word_count": 3000}
```

### 断点恢复

```bash
curl -X POST \
  "http://localhost:8000/api/ai/chapters/chapter-456/resume?story_id=story-123"
```

---

## 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 上下文压缩率 | 40%+ | 降低 Token 成本 |
| Checkpoint 恢复时间 | < 10s | 快速恢复 |
| 查询响应时间 | < 2s | 记忆系统查询 |
| 章节生成时间 | 3000 字 < 2min | 包含规划、生成、检查、评审 |
| 并发用户数 | 1000+ | 系统容量 |
| 一致性问题修复率 | 80%+ | 自动修复成功率 |

---

## 成本估算

**月度成本**（生成 1000 章）: ~$1280

- LLM 调用: $1000
- 数据库 (PostgreSQL): $50
- 缓存 (Redis): $20
- 对象存储 (OSS): $10
- 服务器: $200

---

## 开发指南

### 使用 Claude Skills

项目配置了多个专业 Claude Skills，对应不同开发阶段：

```bash
# 系统架构设计
/system-architect

# 项目规划管理
/project-planner

# LangGraph 工作流开发
/langgraph-architect

# 上下文工程
/context-engineer

# Python 后端开发
/python-backend

# 小说技能工程
/novel-skill-engineer

# 测试工程
/test-engineer

# 代码审查
/reviewer

# 代码重构
/refactor-engineer
```

详见 [.claude/CLAUDE.md](./.claude/CLAUDE.md)

---

## 文档

- [产品需求文档 (PRD)](./docs/PRD.md)
- [需求确认与后端边界](./docs/product/requirements-confirmation.md)
- [系统架构设计](./docs/architecture/system-architecture.md)
- [技术选型总结](./docs/architecture/tech-stack.md)
- [架构决策记录 (ADR)](./docs/architecture/adr/)
- [架构师工作总结](./docs/architecture/ARCHITECT-SUMMARY.md)

---

## 技术演进路线

### Phase 1: MVP（2 个月）
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
- [ ] 小说技能库（20+ 题材）
- [ ] 高级伏笔管理
- [ ] 人工介入机制
- [ ] 监控告警完善

---

## 贡献指南

欢迎贡献代码、提 Issue 或 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 提交 Pull Request

---

## 许可证

本项目采用 MIT 许可证。详见 [LICENSE](./LICENSE) 文件。

---

## 联系方式

- **项目负责人**: louquan
- **项目状态**: 开发中（M1 基础架构搭建阶段）
- **最后更新**: 2026-06-04

---

## 致谢

- [LangGraph](https://langchain-ai.github.io/langgraph/) - Multi-Agent 编排框架
- [LangChain](https://python.langchain.com/) - LLM 应用开发框架
- [FastAPI](https://fastapi.tiangolo.com/) - 现代 Python Web 框架
- [OpenRouter](https://openrouter.ai/) - 统一多模型接口

---

**Star ⭐️ 本项目，关注 AI 写作技术的最新进展！**
