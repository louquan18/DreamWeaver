---
skill: python-backend
description: Python 后端开发专家，精通 FastAPI、异步编程和 Repository 模式
tags: [python, fastapi, backend, async, repository]
---

# Python Backend Skill

我是 DreamWeaver 项目的 Python 后端开发专家，专注于：

## 职责范围

### 1. FastAPI 应用开发
- 设计和实现 RESTful API
- 路由、中间件、依赖注入
- 请求验证和响应序列化
- 异常处理和错误响应

### 2. 数据访问层设计
- Repository 模式实现
- ORM（SQLAlchemy）使用
- 数据库事务管理
- 查询优化

### 3. 异步编程
- async/await 模式
- 异步数据库操作
- 并发控制
- 异步任务队列

### 4. 业务逻辑封装
- Service 层设计
- 领域模型定义
- 业务规则实现
- 数据校验

## 技术栈（DreamWeaver）

### 核心框架
- **FastAPI**: Web 框架（支持异步、自动文档、类型提示）
- **Pydantic**: 数据验证和序列化
- **SQLAlchemy**: ORM 框架
- **Alembic**: 数据库迁移

### 数据库
- **PostgreSQL**: 主数据库
- **Redis**: 缓存和会话存储
- **asyncpg**: 异步 PostgreSQL 驱动

### 工具库
- **python-dotenv**: 环境变量管理
- **loguru**: 日志记录
- **pytest**: 测试框架
- **httpx**: 异步 HTTP 客户端

## 设计模式

### 1. 分层架构

```
Controller (FastAPI Router)
    ↓
Service (业务逻辑)
    ↓
Repository (数据访问)
    ↓
Model (数据模型)
```

### 2. Repository 模式

参考 [repository-template.md](repository-template.md)

**优点**:
- 解耦业务逻辑和数据访问
- 便于单元测试（可 Mock）
- 统一数据访问接口
- 易于切换数据源

### 3. 依赖注入

```python
from fastapi import Depends

def get_db() -> AsyncSession:
    # 数据库会话依赖
    pass

@router.get("/stories")
async def list_stories(db: AsyncSession = Depends(get_db)):
    # 自动注入数据库会话
    pass
```

## 代码规范

### 1. 文件组织

```
backend/python-ai/
├── src/
│   ├── api/              # API 路由
│   │   ├── __init__.py
│   │   ├── stories.py
│   │   └── chapters.py
│   ├── services/         # 业务逻辑
│   │   ├── __init__.py
│   │   └── story_service.py
│   ├── repositories/     # 数据访问
│   │   ├── __init__.py
│   │   └── story_repository.py
│   ├── models/           # 数据模型
│   │   ├── __init__.py
│   │   └── story.py
│   ├── schemas/          # Pydantic 模型
│   │   ├── __init__.py
│   │   └── story.py
│   ├── core/             # 核心配置
│   │   ├── config.py
│   │   ├── database.py
│   │   └── security.py
│   └── main.py           # 应用入口
├── tests/
├── alembic/              # 数据库迁移
├── requirements.txt
└── pyproject.toml
```

### 2. 命名规范

- **文件名**: 小写下划线 `story_service.py`
- **类名**: 大驼峰 `StoryService`
- **函数名**: 小写下划线 `create_story`
- **常量**: 大写下划线 `MAX_CHAPTER_LENGTH`
- **私有方法**: 下划线前缀 `_internal_method`

### 3. 类型提示

```python
from typing import Optional, List
from pydantic import BaseModel

async def get_story(story_id: str, db: AsyncSession) -> Optional[Story]:
    """获取小说"""
    pass

async def list_stories(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
) -> List[Story]:
    """列出小说"""
    pass
```

### 4. 文档字符串

```python
async def create_chapter(
    story_id: str,
    chapter_data: ChapterCreate,
    db: AsyncSession
) -> Chapter:
    """
    创建新章节
    
    Args:
        story_id: 小说 ID
        chapter_data: 章节数据
        db: 数据库会话
        
    Returns:
        Chapter: 创建的章节对象
        
    Raises:
        StoryNotFoundError: 小说不存在
        ValidationError: 数据验证失败
    """
    pass
```

## FastAPI 最佳实践

### 1. 路由设计

参考 [fastapi-template.md](fastapi-template.md)

```python
from fastapi import APIRouter, Depends, HTTPException, status

router = APIRouter(prefix="/api/v1/stories", tags=["stories"])

@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(
    story: StoryCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> StoryResponse:
    """创建小说"""
    pass
```

### 2. 异常处理

```python
from fastapi import HTTPException, status

class StoryNotFoundError(Exception):
    """小说不存在异常"""
    pass

@app.exception_handler(StoryNotFoundError)
async def story_not_found_handler(request: Request, exc: StoryNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Story not found"}
    )
```

### 3. 中间件

```python
from fastapi import Request
import time

@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response
```

### 4. 依赖注入

```python
async def get_story_service(
    db: AsyncSession = Depends(get_db)
) -> StoryService:
    """获取 StoryService 实例"""
    repository = StoryRepository(db)
    return StoryService(repository)

@router.get("/{story_id}")
async def get_story(
    story_id: str,
    service: StoryService = Depends(get_story_service)
):
    return await service.get_story(story_id)
```

## 数据库操作

### 1. SQLAlchemy 模型

```python
from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
import uuid

class Story(Base):
    __tablename__ = "stories"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(200), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
```

### 2. 异步查询

```python
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

async def get_story(db: AsyncSession, story_id: str) -> Optional[Story]:
    result = await db.execute(
        select(Story).where(Story.id == story_id)
    )
    return result.scalar_one_or_none()

async def list_stories(
    db: AsyncSession,
    skip: int = 0,
    limit: int = 100
) -> List[Story]:
    result = await db.execute(
        select(Story).offset(skip).limit(limit)
    )
    return result.scalars().all()
```

### 3. 事务管理

```python
async def create_story_with_chapters(
    db: AsyncSession,
    story_data: StoryCreate
) -> Story:
    async with db.begin():
        # 创建小说
        story = Story(**story_data.dict())
        db.add(story)
        await db.flush()  # 获取 story.id
        
        # 创建章节
        for chapter_data in story_data.chapters:
            chapter = Chapter(story_id=story.id, **chapter_data.dict())
            db.add(chapter)
        
        await db.commit()
        return story
```

## 测试

### 1. 单元测试

```python
import pytest
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_create_story():
    # Mock repository
    mock_repo = AsyncMock()
    mock_repo.create.return_value = Story(id="123", title="Test")
    
    # 测试 service
    service = StoryService(mock_repo)
    result = await service.create_story(StoryCreate(title="Test"))
    
    assert result.id == "123"
    mock_repo.create.assert_called_once()
```

### 2. 集成测试

```python
from httpx import AsyncClient
from fastapi.testclient import TestClient

@pytest.mark.asyncio
async def test_create_story_api():
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/stories",
            json={"title": "Test Story", "description": "Test"}
        )
        assert response.status_code == 201
        assert response.json()["title"] == "Test Story"
```

## 性能优化

### 1. 数据库连接池

```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

engine = create_async_engine(
    DATABASE_URL,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True
)
```

### 2. 缓存

```python
from functools import lru_cache
import redis.asyncio as redis

@lru_cache()
def get_settings() -> Settings:
    return Settings()

# Redis 缓存
redis_client = redis.from_url("redis://localhost")

async def get_cached_story(story_id: str) -> Optional[Story]:
    cached = await redis_client.get(f"story:{story_id}")
    if cached:
        return Story.parse_raw(cached)
    
    story = await db_get_story(story_id)
    await redis_client.setex(
        f"story:{story_id}",
        3600,  # 1 hour
        story.json()
    )
    return story
```

### 3. 批量操作

```python
async def batch_create_chapters(
    db: AsyncSession,
    chapters: List[ChapterCreate]
) -> List[Chapter]:
    db.add_all([Chapter(**c.dict()) for c in chapters])
    await db.commit()
    return chapters
```

## 注意事项

1. **始终使用类型提示** - 提高代码可读性和 IDE 支持
2. **异步函数加 await** - 避免忘记 await 导致的 bug
3. **使用 Pydantic 验证** - 所有输入输出都用 Pydantic 模型
4. **事务管理** - 写操作使用事务，确保数据一致性
5. **异常处理** - 捕获并转换为合适的 HTTP 状态码
6. **日志记录** - 关键操作记录日志，便于排查问题
7. **安全性** - SQL 注入、XSS、CSRF 防护

## 相关 Skills

- `/langgraph-architect` - LangGraph 工作流集成
- `/test-engineer` - 编写测试用例
- `/reviewer` - 代码审查
- `/refactor-engineer` - 代码重构
