# DreamWeaver Issues 清单

**版本**: v1.0  
**日期**: 2026-06-04  
**总任务数**: 94 个

---

## Issues 概览

### 按里程碑分类

| Milestone | Issue 数量 | 总工作量 | 状态 |
|-----------|-----------|---------|------|
| M1: 基础架构搭建 | 10 | 8.5d | Todo |
| M2: LangGraph 工作流核心 | 15 | 23.5d | Todo |
| M3: 上下文管理系统 | 12 | 16.5d | Todo |
| M4: 一致性检查与评审 | 10 | 12.5d | Todo |
| M5: 模型适配与优化 | 8 | 7.5d | Todo |
| M6: SSE 流式输出 | 6 | 6d | Todo |
| M7: 小说技能库 | 8 | 11d | Todo |
| M8: 前端与集成 | 10 | 14d | Todo |
| M9: 测试与优化 | 8 | 10.5d | Todo |
| M10: 文档与部署 | 7 | 7d | Todo |
| **总计** | **94** | **117d** | - |

### 按优先级分类

| 优先级 | Issue 数量 | 工作量 |
|--------|-----------|--------|
| P0 | 52 | 73.5d |
| P1 | 36 | 38d |
| P2 | 6 | 5.5d |

### 按模块分类

| 模块 | Issue 数量 | 负责团队 |
|------|-----------|---------|
| Backend | 18 | Backend Team |
| AI/LangGraph | 46 | AI Team |
| Frontend | 10 | Frontend Team |
| Testing | 8 | QA Team |
| DevOps | 12 | DevOps Team |

---

## Milestone 1: 基础架构搭建

### Issue #1: 创建项目目录结构

**优先级**: P0  
**工作量**: 0.5d  
**负责人**: Backend Lead  
**标签**: setup, infrastructure

**描述**:
创建符合项目规范的目录结构，包含前端、后端、文档等模块。

**验收标准**:
- [ ] `backend/python-ai/` 目录结构创建
- [ ] `backend/java-service/` 目录结构创建
- [ ] `frontend/` 目录结构创建
- [ ] `docs/` 目录结构创建
- [ ] `.gitignore` 配置完成
- [ ] `README.md` 更新

**技术方案**:
```
DreamWeaver/
├── backend/
│   ├── python-ai/
│   │   ├── src/
│   │   │   ├── api/
│   │   │   ├── agents/
│   │   │   ├── workflows/
│   │   │   ├── memory/
│   │   │   ├── models/
│   │   │   └── core/
│   │   ├── tests/
│   │   ├── requirements.txt
│   │   └── pyproject.toml
│   └── java-service/
│       ├── src/main/java/
│       └── pom.xml
├── frontend/
│   ├── src/
│   └── package.json
└── docs/
```

---

### Issue #2: 初始化 Python AI 服务（FastAPI）

**优先级**: P0  
**工作量**: 1d  
**负责人**: Backend Team  
**标签**: backend, python, fastapi  
**依赖**: #1

**描述**:
搭建 FastAPI 服务框架，包含基础路由、中间件、配置管理。

**验收标准**:
- [ ] FastAPI 应用初始化
- [ ] Health Check API 可用
- [ ] CORS 中间件配置
- [ ] 日志配置（Loguru）
- [ ] 环境变量管理（python-dotenv）
- [ ] `uvicorn` 启动脚本

**技术方案**:
```python
# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="DreamWeaver AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```

---

### Issue #3: 初始化 Java 服务（Spring Boot）

**优先级**: P0  
**工作量**: 1d  
**负责人**: Backend Team  
**标签**: backend, java, spring-boot  
**依赖**: #1

**描述**:
搭建 Spring Boot 服务框架，包含用户管理、审计日志基础模块。

**验收标准**:
- [ ] Spring Boot 应用初始化
- [ ] Health Check API 可用
- [ ] JWT 认证配置
- [ ] JPA 配置
- [ ] 日志配置（Logback）
- [ ] `mvn spring-boot:run` 可运行

---

### Issue #4: 设计数据库 Schema

**优先级**: P0  
**工作量**: 1.5d  
**负责人**: Backend Lead  
**标签**: database, schema

**描述**:
设计 PostgreSQL 数据库 Schema，包含 Story、Chapter、Memory、Checkpoint 等表。

**验收标准**:
- [ ] ER 图设计完成
- [ ] DDL SQL 脚本编写
- [ ] 索引设计
- [ ] 约束定义

**技术方案**:
```sql
-- stories 表
CREATE TABLE stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    genre VARCHAR(50),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

-- chapters 表
CREATE TABLE chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id),
    chapter_number INT NOT NULL,
    title VARCHAR(200),
    content_url TEXT,
    word_count INT,
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(story_id, chapter_number)
);

-- story_memories 表
CREATE TABLE story_memories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id),
    memory_type VARCHAR(50),
    content JSONB NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_memories_story_type ON story_memories(story_id, memory_type);
```

---

### Issue #5: 实现数据库迁移脚本（Alembic）

**优先级**: P0  
**工作量**: 1d  
**负责人**: Backend Team  
**标签**: database, migration  
**依赖**: #4

**描述**:
使用 Alembic 实现数据库版本管理和迁移脚本。

**验收标准**:
- [ ] Alembic 配置完成
- [ ] 初始迁移脚本生成
- [ ] `alembic upgrade head` 可执行
- [ ] `alembic downgrade` 可回滚

---

### Issue #6: 配置 Redis 缓存

**优先级**: P1  
**工作量**: 0.5d  
**负责人**: Backend Team  
**标签**: cache, redis

**描述**:
配置 Redis 缓存，实现会话管理和热数据缓存。

**验收标准**:
- [ ] Redis 连接配置
- [ ] 会话管理实现
- [ ] 缓存工具类封装
- [ ] 缓存过期策略配置

---

### Issue #7: 配置 OSS 对象存储

**优先级**: P1  
**工作量**: 0.5d  
**负责人**: Backend Team  
**标签**: storage, oss

**描述**:
配置对象存储服务，用于保存章节完整内容。

**验收标准**:
- [ ] OSS SDK 集成
- [ ] 上传/下载接口实现
- [ ] URL 签名生成

---

### Issue #8: Docker Compose 环境配置

**优先级**: P0  
**工作量**: 1d  
**负责人**: DevOps Team  
**标签**: docker, devops  
**依赖**: #2, #3

**描述**:
配置 Docker Compose 本地开发环境，包含所有服务。

**验收标准**:
- [ ] `docker-compose.yml` 配置完成
- [ ] PostgreSQL 服务配置
- [ ] Redis 服务配置
- [ ] Python AI 服务 Dockerfile
- [ ] Java 服务 Dockerfile
- [ ] `docker-compose up` 可启动所有服务

**技术方案**:
```yaml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: dreamweaver
      POSTGRES_USER: user
      POSTGRES_PASSWORD: password
    ports:
      - "5432:5432"
  
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
  
  python-ai:
    build: ./backend/python-ai
    ports:
      - "8000:8000"
    depends_on:
      - postgres
      - redis
  
  java-service:
    build: ./backend/java-service
    ports:
      - "8080:8080"
    depends_on:
      - postgres
      - redis
```

---

### Issue #9: 基础 API 端点（Health Check）

**优先级**: P1  
**工作量**: 0.5d  
**负责人**: Backend Team  
**标签**: api, monitoring  
**依赖**: #2

**描述**:
实现健康检查和服务状态监控端点。

**验收标准**:
- [ ] `/health` 端点返回服务状态
- [ ] `/metrics` 端点返回指标（可选）
- [ ] 数据库连接检查
- [ ] Redis 连接检查

---

### Issue #10: GitHub Actions CI/CD 配置

**优先级**: P1  
**工作量**: 1d  
**负责人**: DevOps Team  
**标签**: ci-cd, github-actions  
**依赖**: #8

**描述**:
配置 GitHub Actions 自动化测试和部署流水线。

**验收标准**:
- [ ] `.github/workflows/ci.yml` 配置
- [ ] Python 单元测试自动运行
- [ ] Java 单元测试自动运行
- [ ] Docker 镜像自动构建
- [ ] 代码风格检查（Black、Pylint）

---

## Milestone 2: LangGraph 工作流核心（仅展示前 5 个 Issue）

### Issue #11: 定义 NovelState TypedDict Schema

**优先级**: P0  
**工作量**: 1d  
**负责人**: AI Team Lead  
**标签**: langgraph, schema

**描述**:
定义 LangGraph 工作流的状态结构。

**验收标准**:
- [ ] `NovelState` TypedDict 定义完成
- [ ] 包含所有必要字段
- [ ] 类型注解完整
- [ ] 文档注释清晰

**技术方案**:
```python
from typing import TypedDict, Optional, List, Dict, Any

class NovelState(TypedDict, total=False):
    story_id: str
    chapter_id: str
    user_id: str
    novel_context: Dict[str, Any]
    chapter_outline: Dict[str, Any]
    generated_draft: str
    consistency_report: Dict[str, Any]
    review_report: Dict[str, Any]
    execution_history: List[str]
    current_node: Optional[str]
    checkpoint_id: Optional[str]
    error: Optional[str]
    retry_count: int
    metadata: Dict[str, Any]
```

---

### Issue #12: 实现 LLM Provider 抽象层

**优先级**: P0  
**工作量**: 1.5d  
**负责人**: AI Team  
**标签**: llm, provider

**描述**:
创建 LLM Provider 抽象层，统一不同模型的调用接口。

**验收标准**:
- [ ] `LLMProvider` 抽象类定义
- [ ] `generate()` 方法
- [ ] `stream()` 方法
- [ ] 错误处理和重试机制

---

### Issue #13: 实现 Context Agent

**优先级**: P0  
**工作量**: 2d  
**负责人**: AI Team  
**标签**: agent, context  
**依赖**: #11

**描述**:
实现 Context Agent，负责加载历史章节和构建上下文。

**验收标准**:
- [ ] 历史章节检索实现
- [ ] 上下文组装逻辑
- [ ] 返回 `novel_context` 结构
- [ ] 单元测试覆盖

---

### Issue #14: 实现 Planner Agent

**优先级**: P0  
**工作量**: 2d  
**负责人**: AI Team  
**标签**: agent, planner  
**依赖**: #11

**描述**:
实现 Planner Agent，负责章节规划和大纲生成。

**验收标准**:
- [ ] 基于上下文生成章节大纲
- [ ] 返回 `chapter_outline` 结构
- [ ] Prompt 模板优化
- [ ] 单元测试覆盖

---

### Issue #15: 实现 Writer Agent

**优先级**: P0  
**工作量**: 2.5d  
**负责人**: AI Team  
**标签**: agent, writer  
**依赖**: #11

**描述**:
实现 Writer Agent，负责生成章节草稿（支持流式输出）。

**验收标准**:
- [ ] 基于大纲生成章节内容
- [ ] 支持流式输出（Token 级）
- [ ] 返回 `generated_draft`
- [ ] 文风一致性保持
- [ ] 单元测试覆盖

---

## 快速开始 Issues

### 本周建议启动的 Issues（前 5 个）

1. **Issue #1**: 创建项目目录结构 - 0.5d
2. **Issue #2**: 初始化 Python AI 服务 - 1d
3. **Issue #3**: 初始化 Java 服务 - 1d
4. **Issue #4**: 设计数据库 Schema - 1.5d
5. **Issue #8**: Docker Compose 环境配置 - 1d

**总工作量**: 5 天  
**建议人员**: Backend Team (2人) + DevOps (1人)

---

## Issue 模板

### 新建 Issue 时使用以下模板

```markdown
## Issue #XX: [任务名称]

**优先级**: P0/P1/P2  
**工作量**: Xd  
**负责人**: [Team/Person]  
**标签**: [tag1, tag2]  
**依赖**: #XX, #XX

### 描述
[详细描述任务内容]

### 验收标准
- [ ] 标准 1
- [ ] 标准 2
- [ ] 标准 3

### 技术方案（可选）
```code
```

### 相关文档
- [链接到相关文档]
```

---

## 进度追踪

### 每周更新

建议每周一召开站会，更新 Issue 状态：
- **Todo**: 待开始
- **In Progress**: 进行中
- **Blocked**: 阻塞
- **Review**: 代码审查中
- **Done**: 已完成

### Kanban 看板

推荐使用 GitHub Projects 创建 Kanban 看板：
```
Todo | In Progress | Review | Done
-----|-------------|--------|-----
#1   | #2          | #5     | 
#3   | #4          |        |
#6   |             |        |
```

---

## 附录

### Issue 标签说明

| 标签 | 说明 |
|------|------|
| setup | 项目搭建 |
| backend | 后端开发 |
| frontend | 前端开发 |
| agent | Agent 开发 |
| langgraph | LangGraph 相关 |
| database | 数据库相关 |
| testing | 测试相关 |
| devops | 运维部署 |
| bug | Bug 修复 |
| enhancement | 功能增强 |

---

**最后更新**: 2026-06-04  
**维护人**: Project Manager
