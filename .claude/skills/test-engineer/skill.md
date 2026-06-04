---
skill: test-engineer
description: 测试工程专家，负责单元测试、集成测试和性能测试
tags: [testing, pytest, unittest, integration-test]
---

# Test Engineer Skill

我是 DreamWeaver 项目的测试工程专家，专注于：

## 职责范围

### 1. 单元测试
- Repository 层测试
- Service 层测试
- Agent 节点测试
- 工具函数测试

### 2. 集成测试
- API 端到端测试
- LangGraph 工作流测试
- 数据库集成测试

### 3. 性能测试
- 响应时间测试
- 并发测试
- 压力测试

## 测试框架

- **pytest**: 主测试框架
- **pytest-asyncio**: 异步测试支持
- **httpx**: 异步 HTTP 测试
- **unittest.mock**: Mock 支持

## 单元测试模板

参考 [unit-test-template.md](unit-test-template.md)

### Repository 测试

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_story(db: AsyncSession):
    """测试创建小说"""
    repo = StoryRepository(db)
    
    story_data = StoryCreate(
        title="测试小说",
        description="测试描述",
        genre="玄幻"
    )
    
    story = await repo.create(story_data, user_id="user-123")
    
    assert story.id is not None
    assert story.title == "测试小说"
    assert story.user_id == "user-123"
```

### Service 测试（使用 Mock）

```python
from unittest.mock import AsyncMock

@pytest.mark.asyncio
async def test_story_service_create():
    """测试 StoryService.create"""
    
    # Mock repository
    mock_repo = AsyncMock()
    mock_repo.create.return_value = Story(
        id="story-123",
        title="测试",
        user_id="user-123"
    )
    
    # 测试 service
    service = StoryService(mock_repo)
    result = await service.create_story(
        StoryCreate(title="测试", genre="玄幻"),
        user_id="user-123"
    )
    
    assert result.id == "story-123"
    mock_repo.create.assert_called_once()
```

### Agent 节点测试

```python
@pytest.mark.asyncio
async def test_context_agent_node():
    """测试 Context Agent 节点"""
    
    # 准备状态
    state = NovelState(
        story_id="story-123",
        chapter_id="chapter-456",
        novel_context={},
        execution_history=[]
    )
    
    # 执行节点
    result = await context_agent_node(state)
    
    # 断言
    assert "novel_context" in result
    assert "novel_context" in result["execution_history"]
    assert result["novel_context"] is not None
```

## 集成测试模板

参考 [integration-test-template.md](integration-test-template.md)

### API 集成测试

```python
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_create_story_api():
    """测试创建小说 API"""
    
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/stories",
            json={
                "title": "测试小说",
                "description": "测试",
                "genre": "玄幻"
            },
            headers={"Authorization": f"Bearer {test_token}"}
        )
        
        assert response.status_code == 201
        data = response.json()
        assert data["title"] == "测试小说"
        assert "id" in data
```

### LangGraph 工作流测试

```python
@pytest.mark.asyncio
async def test_chapter_generation_workflow():
    """测试章节生成工作流"""
    
    initial_state = NovelState(
        story_id="test-story",
        chapter_id="test-chapter",
        novel_context={},
        chapter_outline={},
        generated_draft="",
        execution_history=[]
    )
    
    config = {
        "configurable": {
            "thread_id": "test-story-test-chapter"
        }
    }
    
    # 执行工作流
    final_state = await app.ainvoke(initial_state, config)
    
    # 断言
    assert final_state["generated_draft"] != ""
    assert "commit" in final_state["execution_history"]
```

## 测试覆盖率

```bash
# 运行测试并生成覆盖率报告
pytest --cov=src --cov-report=html --cov-report=term

# 目标覆盖率 > 80%
```

## 最佳实践

1. **AAA 模式** - Arrange, Act, Assert
2. **独立测试** - 每个测试独立运行
3. **Mock 外部依赖** - 隔离测试
4. **清理测试数据** - 使用 fixture 自动清理
5. **测试命名清晰** - test_<function>_<scenario>
6. **覆盖边界情况** - 正常、异常、边界

## 相关 Skills

- `/python-backend` - 被测试的代码
- `/langgraph-architect` - 工作流测试
- `/reviewer` - 代码审查
