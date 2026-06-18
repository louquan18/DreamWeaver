# DreamWeaver 系统架构设计文档

**版本**: v1.1（2026-06-17 校订）  
**日期**: 2026-06-04（初版） / 2026-06-17（校订）  
**作者**: System Architect  
**状态**: Draft（目标设计）

> ⚠️ 本文档描述**目标架构**。各能力是否已实现，以 [实现状态总表 STATUS.md](../STATUS.md) 为唯一权威；本文涉及实现进度处均已标注指向。SSE 事件契约与 State Schema 以 Python 代码为权威源。

---

## 1. 系统概述

### 1.1 项目背景

DreamWeaver（织梦者）是一套面向长篇网络小说创作场景的 Multi-Agent AI 写作系统。系统基于 LangGraph 构建 Agent 工作流，通过多阶段协作机制完成小说创作的完整闭环。

### 1.2 核心目标

**功能目标**:
- 支持完整小说创作流程（题材输入 → 世界观构建 → 小说规划 → 章节生成 → 一致性检查 → 评审优化 → 章节提交）
- 实现 AI 自评审、自修复闭环
- 提供实时流式输出体验

**技术目标**:
- **可扩展**: 支持多模型接入（GPT/Claude/Gemini/DeepSeek/Qwen）
- **可恢复**: 任务断点恢复，恢复时间 < 10s
- **可观测**: 实时状态追踪，SSE 流式输出
- **低成本**: 上下文压缩率 40%+
- **高一致性**: 一致性问题修复率 80%+

### 1.3 关键挑战

1. **长文本上下文窗口限制** - 100 万字+ 小说无法全量输入
2. **长篇创作情节一致性** - 人物设定漂移、情节冲突、伏笔遗失
3. **多 Agent 协作复杂度** - 8+ Agent 节点协同工作
4. **任务中断恢复** - 长时间任务需要支持断点续写
5. **成本控制** - LLM 调用成本高，需要优化

---

## 2. 系统架构

### 2.1 总体架构图

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend Layer                        │
│                   React + TypeScript + SSE                   │
│  ┌────────────┐  ┌────────────┐  ┌────────────────────────┐ │
│  │ 创作控制台  │  │ 实时预览    │  │ Agent 状态可视化        │ │
│  └────────────┘  └────────────┘  └────────────────────────┘ │
└───────────────────────────┬─────────────────────────────────┘
                            │ HTTPS / SSE
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                       │
│                    Nginx / API Gateway                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ 认证/授权     │  │ 限流/熔断     │  │ 负载均衡          │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
└───────────────┬──────────────────────────┬──────────────────┘
                │                          │
      ┌─────────▼─────────┐    ┌──────────▼───────────┐
      │   Java Service    │    │  Python AI Service   │
      │   Spring Boot     │    │  FastAPI + LangGraph │
      └───────────────────┘    └──────────────────────┘
                │                          │
      ┌─────────▼─────────┐    ┌──────────▼───────────┐
      │ • 用户管理         │    │ • Agent 工作流引擎    │
      │ • 小说元数据管理   │    │ • Context Manager    │
      │ • 审计日志         │    │ • Memory Manager     │
      │ • 权限控制         │    │ • Model Provider     │
      └─────────┬─────────┘    │ • Checkpoint Manager │
                │                └──────────┬───────────┘
                │                          │
                └──────────┬───────────────┘
                           │
        ┌──────────────────▼──────────────────┐
        │           Data Layer                │
        │  ┌──────────┐  ┌────────┐  ┌──────┐│
        │  │PostgreSQL│  │ Redis  │  │ OSS  ││
        │  │主数据库   │  │缓存层  │  │对象存储││
        │  └──────────┘  └────────┘  └──────┘│
        └─────────────────────────────────────┘
```

### 2.2 分层架构说明

#### 2.2.1 前端层（Frontend Layer）

**技术栈**: React + TypeScript + Vite

**职责**:
- 用户交互界面
- 实时 SSE 连接管理
- Agent 状态可视化
- 章节内容编辑

**关键组件**:
- `CreationConsole`: 创作控制台（启动/暂停/恢复）
- `LivePreview`: 实时预览组件（Token 级流式显示）
- `AgentStatusBoard`: Agent 状态看板
- `ChapterEditor`: 章节编辑器

#### 2.2.2 API 网关层（API Gateway）

**技术栈**: Nginx 或云厂商 API Gateway

**职责**:
- 统一入口
- 认证授权
- 限流熔断
- 负载均衡
- SSL 终止

**配置**:
```nginx
# 反向代理示例
location /api/java/ {
    proxy_pass http://java-service:8080/;
}

location /api/ai/ {
    proxy_pass http://python-ai:8000/;
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";  # SSE 支持
}
```

#### 2.2.3 Java 服务层（Java Service）

**技术栈**: Spring Boot 3.x + Spring Data JPA

**职责**:
- 用户认证与授权
- 小说元数据管理（CRUD）
- 审计日志记录
- 权限控制

**核心模块**:
```
java-service/
├── src/main/java/com/dreamweaver/
│   ├── controller/       # REST 控制器
│   ├── service/          # 业务逻辑
│   ├── repository/       # 数据访问
│   ├── entity/           # JPA 实体
│   ├── security/         # 安全配置
│   └── audit/            # 审计日志
```

#### 2.2.4 Python AI 服务层（Python AI Service）

**技术栈**: FastAPI + LangGraph + LangChain

**职责**:
- Agent 工作流编排
- 上下文管理
- 记忆系统管理
- 多模型调用
- Checkpoint 管理

**核心模块**:
```
python-ai/
├── src/
│   ├── api/              # FastAPI 路由
│   ├── agents/           # Agent 实现
│   │   ├── context_agent.py
│   │   ├── planner_agent.py
│   │   ├── writer_agent.py
│   │   ├── consistency_agent.py
│   │   ├── reviewer_agent.py
│   │   └── rewrite_agent.py
│   ├── workflows/        # LangGraph 工作流
│   │   ├── state.py      # State Schema
│   │   ├── graph.py      # 工作流定义
│   │   └── nodes.py      # 节点实现
│   ├── memory/           # 记忆系统
│   │   ├── timeline.py
│   │   ├── character_graph.py
│   │   ├── foreshadow.py
│   │   └── world_state.py
│   ├── models/           # 模型层
│   │   ├── provider.py   # 模型提供者抽象
│   │   └── router.py     # 模型路由
│   ├── checkpoint/       # Checkpoint 管理
│   └── core/             # 核心配置
```

#### 2.2.5 数据层（Data Layer）

**PostgreSQL**:
- 用户数据
- 小说元数据（标题、简介、设定）
- Agent 执行历史
- Checkpoint 快照

**Redis**:
- 用户会话
- Agent 状态缓存
- 热数据缓存（常用人物、世界观）

**Object Storage (OSS)**:
- 章节完整内容
- 压缩后的历史章节

---

## 3. Agent 工作流架构

### 3.1 LangGraph 状态机设计

```
                  START
                    │
                    ▼
        ┌───────────────────────┐
        │ load_runtime_context  │  加载运行时上下文
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │    novel_context      │  构建小说上下文
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │    plan_chapter       │  规划章节
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │   generate_draft      │  生成草稿（流式）
        └───────────┬───────────┘
                    │
                    ▼
        ┌───────────────────────┐
        │  check_consistency    │  一致性检查
        └───────────┬───────────┘
                    │
            ┌───────┴────────┐
            │                │
     (有问题)          (无问题直接提交)
            ▼                │
    ┌────────────┐          │
    │   review   │          │
    └──────┬─────┘          │
      分数低│ │分数高         │
           │ └───────────────┤
           ▼                 ▼
    ┌────────────┐    ┌───────────┐
    │  rewrite   │    │  commit   │
    └──────┬─────┘    └─────┬─────┘
           │                │
           └──► review       ▼
        （rewrite 后回到     END
          review，循环）
```

### 3.2 State Schema

> 权威源：以 `backend/python-ai/src/workflows/state.py` 为准。下方为目标示意，**注意当前代码中并无 `checkpoint_id` 字段**（详见 [STATUS.md](../STATUS.md) 第 3 节）。

```python
from typing import TypedDict, Optional, List, Dict, Any

class NovelState(TypedDict, total=False):
    # 基础信息
    story_id: str
    chapter_id: str
    user_id: str
    
    # 上下文信息
    novel_context: Dict[str, Any]      # Timeline, Characters, Foreshadows, World
    chapter_outline: Dict[str, Any]    # 章节大纲
    
    # 生成内容
    generated_draft: str               # 章节草稿
    
    # 检查报告
    consistency_report: Dict[str, Any] # 一致性报告
    review_report: Dict[str, Any]      # 评审报告
    
    # 执行状态
    execution_history: List[str]       # 已执行节点
    current_node: Optional[str]        # 当前节点
    
    # Checkpoint
    checkpoint_id: Optional[str]
    
    # 错误处理
    error: Optional[str]
    retry_count: int
    
    # 元数据
    metadata: Dict[str, Any]
```

### 3.3 Agent 节点设计

#### Context Agent
**输入**: story_id, chapter_id  
**输出**: novel_context  
**职责**:
- 加载最近 5 章内容
- 提取人物当前状态
- 构建时间线
- 加载活跃伏笔
- 加载世界观状态

#### Planner Agent
**输入**: novel_context  
**输出**: chapter_outline  
**职责**:
- 分析剧情进度
- 设计章节目标
- 规划冲突设置
- 确定关键情节点

#### Writer Agent
**输入**: chapter_outline, novel_context  
**输出**: generated_draft  
**职责**:
- 根据大纲生成章节
- 流式输出（Token 级）
- 保持文风一致

#### Consistency Agent
**输入**: generated_draft, novel_context  
**输出**: consistency_report  
**职责**:
- 检测人物一致性（性格、能力、关系）
- 检测世界观一致性（规则、设定）
- 检测情节一致性（伏笔、因果）

#### Reviewer Agent
**输入**: generated_draft, consistency_report  
**输出**: review_report  
**职责**:
- 评估语言质量
- 评估节奏控制
- 评估冲突强度
- 给出修改建议

#### Rewrite Agent
**输入**: generated_draft, review_report  
**输出**: generated_draft (updated)  
**职责**:
- 定位问题段落
- 局部重写
- 保持整体连贯

---

## 4. 核心子系统设计

### 4.1 结构化记忆系统

#### 设计目标
- 压缩率 40%+
- 查询响应时间 < 2s
- 支持语义检索

#### 四层记忆结构

**1. Timeline（时间线）**
```python
{
    "events": [
        {
            "chapter": 15,
            "event": "主角获得系统",
            "characters": ["主角"],
            "importance": "high"
        }
    ]
}
```

**2. Character Graph（人物关系图）**
```python
{
    "张三": {
        "current_state": {
            "level": 50,
            "location": "天元城"
        },
        "relationships": {
            "李四": {"type": "好友", "closeness": 80}
        }
    }
}
```

**3. Foreshadow Memory（伏笔记忆）**
```python
{
    "foreshadows": [
        {
            "id": "foreshadow-001",
            "chapter_planted": 10,
            "content": "神秘老人提到上古秘境",
            "status": "active"
        }
    ]
}
```

**4. World State（世界状态）**
```python
{
    "forces": {
        "天元宗": {"strength": "strong", "attitude": "friendly"}
    },
    "rules": {
        "修炼体系": "炼气 → 筑基 → 金丹 → 元婴"
    }
}
```

### 4.2 上下文压缩流水线

```
原始章节 (3000字)
    │
    ▼
事件抽取 ──→ Timeline Events (5-10 条)
    │
    ▼
人物变化 ──→ Character Updates (2-5 个)
    │
    ▼
摘要生成 ──→ Summary (200 字)
    │
    ▼
结构化存储 ──→ Compressed Context (约 1000 字)

压缩率 = 1 - (1000 / 3000) ≈ 67%
```

### 4.3 Checkpoint 恢复机制

> ❌ **现状（2026-06-17）**：尚未实现。代码当前使用 `MemorySaver()`（内存态，进程重启即丢失），`checkpoint/` 目录为空，下述 PostgreSQL 持久化与 <10s 恢复均为目标，未落地。详见 [STATUS.md](../STATUS.md) 第 4 节、[ADR-003](./adr/ADR-003-checkpoint.md)。

#### Checkpoint 数据结构

```python
{
    "execution_id": "exec-20260604-001",
    "story_id": "story-123",
    "chapter_id": "chapter-456",
    "current_node": "generate_draft",
    "state_snapshot": {
        # NovelState 完整快照
    },
    "timestamp": "2026-06-04T10:30:00Z",
    "version": "1.0"
}
```

#### 恢复流程

```
任务中断
    │
    ▼
检测到 Checkpoint
    │
    ▼
加载 State Snapshot
    │
    ▼
定位 current_node
    │
    ▼
从中断点继续执行
```

**性能指标**:
- Checkpoint 保存频率: 每个节点完成后
- Checkpoint 大小: < 100KB（压缩后）
- 恢复时间: < 10s

### 4.4 多模型适配层

> 🚧 **现状（2026-06-17）**：已有"按 Agent 选模型 + 温度"的机制（`models/provider.py`），但六个 Agent 当前**全部配置为 `mimo-7b` 单一模型**（`core/config.py`），无独立 `router.py`、无按任务切换、无自动 Fallback。下表为目标路由策略。详见 [STATUS.md](../STATUS.md) 第 5 节、[ADR-004](./adr/ADR-004-multi-model-routing.md)。

#### Provider 抽象

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass
    
    @abstractmethod
    async def stream(self, prompt: str, **kwargs):
        pass
    
    @abstractmethod
    async def embedding(self, text: str) -> List[float]:
        pass
```

#### 模型路由策略

| 任务类型 | 推荐模型 | 理由 |
|---------|---------|------|
| 章节规划 | Claude-3.5-Sonnet / GPT-4 | 推理能力强 |
| 章节写作 | Claude-3.5-Sonnet-200k | 长文本支持 |
| 一致性检查 | GPT-3.5-Turbo / Haiku | 低成本 |
| 评审优化 | Claude-3-Opus / GPT-4 | 高质量 |
| 事件抽取 | DeepSeek-v3 / Qwen-Max | 中文优化 |

#### OpenRouter 集成

```python
import openai

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)

response = await client.chat.completions.create(
    model="anthropic/claude-3.5-sonnet",  # 指定模型
    messages=[...],
    stream=True
)
```

---

## 5. 数据模型设计

### 5.1 核心实体

#### Story（小说）
```sql
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id),
    title VARCHAR(200) NOT NULL,
    description TEXT,
    genre VARCHAR(50),  -- 玄幻、都市、系统流等
    target_words INT,   -- 目标字数
    status VARCHAR(20), -- draft, writing, completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Chapter（章节）
```sql
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id),
    chapter_number INT NOT NULL,
    title VARCHAR(200),
    content_url TEXT,    -- OSS URL
    word_count INT,
    status VARCHAR(20),  -- draft, writing, completed
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(story_id, chapter_number)
);
```

#### Memory（记忆）
```sql
CREATE TABLE story_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id),
    memory_type VARCHAR(50),  -- timeline, character, foreshadow, world
    content JSONB NOT NULL,
    chapter_range INT[],      -- [start_chapter, end_chapter]
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memories_story_type ON story_memories(story_id, memory_type);
CREATE INDEX idx_memories_content ON story_memories USING GIN(content);
```

#### Checkpoint（断点）
```sql
CREATE TABLE checkpoints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    execution_id VARCHAR(100) UNIQUE NOT NULL,
    story_id UUID NOT NULL REFERENCES stories(id),
    chapter_id UUID NOT NULL REFERENCES chapters(id),
    current_node VARCHAR(100),
    state_snapshot JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_checkpoints_execution ON checkpoints(execution_id);
```

> 📌 **补充（2026-06-17）**：本节遗漏了 `chapter_generations` 表与 `chapters.last_generation_id` / `chapters.content` 字段——它们是"生成历史/采用版本"闭环的核心，定义见 [章节生成需求与表设计](../product/chapter-generation-requirements.md)，并已在 Java 侧落地（`entity/ChapterGeneration.java`）。后续应将其完整 DDL 并入本节。

### 5.2 缓存策略

**Redis Key 设计**:
```
# 用户会话
session:{user_id} -> {session_data}

# Agent 状态
agent:status:{execution_id} -> {current_node, progress}

# 热数据缓存
story:context:{story_id} -> {timeline, characters, foreshadows}

# 限流
ratelimit:{user_id}:{api} -> count

# TTL 设置
session: 24h
agent:status: 1h
story:context: 30min
```

---

## 6. 接口设计

### 6.1 RESTful API

#### 小说管理（Java Service）

```
POST   /api/stories              创建小说
GET    /api/stories              列出小说
GET    /api/stories/{id}         获取小说详情
PUT    /api/stories/{id}         更新小说
DELETE /api/stories/{id}         删除小说
```

#### 章节生成（Python AI Service）

```
POST   /api/ai/chapters/generate      生成章节（同步）
POST   /api/ai/chapters/generate-stream  生成章节（SSE 流式）
GET    /api/ai/chapters/{id}/status   查询章节生成状态
POST   /api/ai/chapters/{id}/resume   从 Checkpoint 恢复
```

### 6.2 SSE 流式输出

> 权威源：SSE 事件契约以 `backend/python-ai/src/api/routes/chapters.py` 为准（详见 [STATUS.md](../STATUS.md) 第 2 节）。实际事件：`token` / `node_start` / `node_end` / `done` / `error`。**注意**：`node_start/node_end` 与进度值当前为硬编码顺序发出，并非真实节点驱动；无独立 `progress` 事件。下方为目标格式示意。

**连接建立**:
```
GET /api/ai/chapters/generate-stream?story_id=xxx&chapter_id=xxx
Accept: text/event-stream
```

**事件格式**:
```
# Token 流
event: token
data: {"content": "第"}

event: token
data: {"content": "一"}

# 节点状态
event: node_start
data: {"node": "generate_draft"}

event: node_end
data: {"node": "generate_draft"}

# 进度
event: progress
data: {"percent": 65}

# 完成
event: done
data: {"chapter_id": "xxx", "word_count": 3000}
```

---

## 7. 部署架构

### 7.1 容器化方案

```yaml
# docker-compose.yml
services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
      - "443:443"
  
  java-service:
    build: ./backend/java-service
    environment:
      - SPRING_PROFILES_ACTIVE=prod
    depends_on:
      - postgres
      - redis
  
  python-ai:
    build: ./backend/python-ai
    environment:
      - ENV=prod
    depends_on:
      - postgres
      - redis
  
  postgres:
    image: postgres:15
    volumes:
      - postgres_data:/var/lib/postgresql/data
  
  redis:
    image: redis:7-alpine

  # 向量库：代码依赖 Chroma（memory/vector_store.py + chroma_* 配置）
  chroma:
    image: chromadb/chroma:latest
    ports:
      - "8100:8000"
```

> 📌 **说明（2026-06-17）**：本节 compose 为简化示意。根目录实际的 `docker-compose.yml` 已完整编排 `chroma`（含持久化卷）以及 `frontend`、healthcheck 等，请以根目录文件为部署依据。

### 7.2 扩展方案

**水平扩展**:
- Java Service: 无状态，可水平扩展
- Python AI Service: 无状态，可水平扩展（Checkpoint 在数据库）

**垂直扩展**:
- PostgreSQL: 读写分离 + 主从复制
- Redis: Redis Cluster

---

## 8. 非功能性需求

### 8.1 性能指标

| 指标 | 目标值 | 监控方式 |
|------|--------|---------|
| API 响应时间 | P95 < 500ms | APM |
| 章节生成时间 | 3000 字 < 2min | 业务监控 |
| 上下文压缩率 | > 40% | 自定义指标 |
| Checkpoint 恢复 | < 10s | 业务监控 |
| 并发用户数 | 1000+ | 压测 |

### 8.2 可用性

- 目标可用性: 99.9%（允许每月 43 分钟停机）
- 容错策略:
  - 数据库主从切换
  - 服务多实例部署
  - Checkpoint 自动保存

### 8.3 安全性

> ❌ **现状（2026-06-17）**：下列安全能力**均未实现**。Java `security/`、`audit/` 包仅有空 `package-info.java`，`user_id` 当前可空/模拟。本节为目标设计，请勿据此判断系统已有安全防护。详见 [STATUS.md](../STATUS.md) 第 7 节。

- 认证: JWT Token（📋 未实现）
- 授权: RBAC（Role-Based Access Control）（📋 未实现）
- 数据加密: HTTPS + 数据库加密（📋 未实现）
- API 限流: 100 req/min per user（📋 未实现）

---

## 9. 风险评估

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| LLM API 不稳定 | 高 | 中 | 多模型冗余 + 重试机制 |
| 上下文压缩失效 | 中 | 低 | 混合检索 + 人工审核 |
| Checkpoint 损坏 | 高 | 低 | 多版本备份 + 校验 |
| 成本超预算 | 中 | 中 | 成本监控 + 模型路由优化 |
| 生成内容质量低 | 中 | 中 | 多轮评审 + 人工介入 |

---

## 10. 技术演进路线

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

---

## 11. 附录

### 11.1 术语表

| 术语 | 解释 |
|------|------|
| Agent | LangGraph 工作流中的节点，执行特定任务 |
| State | 工作流状态，通过 TypedDict 定义 |
| Checkpoint | 工作流执行的快照，用于恢复 |
| SSE | Server-Sent Events，服务器推送技术 |
| Memory | 结构化记忆，包含 Timeline/Character/Foreshadow/World |

### 11.2 参考资料

- [LangGraph 官方文档](https://langchain-ai.github.io/langgraph/)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
- [Spring Boot 文档](https://spring.io/projects/spring-boot)
- [PostgreSQL 文档](https://www.postgresql.org/docs/)

---

**文档版本历史**

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| v1.0 | 2026-06-04 | System Architect | 初始版本 |
