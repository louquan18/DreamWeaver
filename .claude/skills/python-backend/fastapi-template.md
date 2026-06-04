# FastAPI 路由模板

## 基础路由结构

```python
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional

from ..core.database import get_db
from ..schemas.story import StoryCreate, StoryUpdate, StoryResponse
from ..services.story_service import StoryService
from ..core.security import get_current_user
from ..models.user import User

router = APIRouter(
    prefix="/api/v1/stories",
    tags=["stories"],
    responses={404: {"description": "Not found"}}
)

# 依赖注入
async def get_story_service(db: AsyncSession = Depends(get_db)) -> StoryService:
    """获取 StoryService 实例"""
    from ..repositories.story_repository import StoryRepository
    repository = StoryRepository(db)
    return StoryService(repository)
```

---

## CRUD 操作示例

### 1. Create - 创建资源

```python
@router.post(
    "",
    response_model=StoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建小说",
    description="创建一篇新的小说"
)
async def create_story(
    story: StoryCreate,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> StoryResponse:
    """
    创建小说
    
    - **title**: 小说标题（必填，最长 200 字符）
    - **description**: 小说简介（可选）
    - **genre**: 题材类型（如 "玄幻", "都市"）
    """
    try:
        result = await service.create_story(story, user_id=current_user.id)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### 2. Read - 获取单个资源

```python
@router.get(
    "/{story_id}",
    response_model=StoryResponse,
    summary="获取小说详情",
    responses={
        200: {"description": "成功返回小说详情"},
        404: {"description": "小说不存在"}
    }
)
async def get_story(
    story_id: str,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> StoryResponse:
    """
    根据 ID 获取小说详情
    
    Args:
        story_id: 小说 ID (UUID)
    """
    story = await service.get_story(story_id, user_id=current_user.id)
    if not story:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found"
        )
    return story
```

### 3. List - 获取资源列表

```python
@router.get(
    "",
    response_model=List[StoryResponse],
    summary="获取小说列表"
)
async def list_stories(
    skip: int = Query(0, ge=0, description="跳过的记录数"),
    limit: int = Query(100, ge=1, le=1000, description="返回的最大记录数"),
    genre: Optional[str] = Query(None, description="按题材类型筛选"),
    search: Optional[str] = Query(None, description="搜索关键词"),
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> List[StoryResponse]:
    """
    获取小说列表，支持分页和筛选
    
    - **skip**: 跳过前 N 条记录（用于分页）
    - **limit**: 返回最多 N 条记录（1-1000）
    - **genre**: 按题材类型筛选（可选）
    - **search**: 按标题或简介搜索（可选）
    """
    stories = await service.list_stories(
        skip=skip,
        limit=limit,
        genre=genre,
        search=search,
        user_id=current_user.id
    )
    return stories
```

### 4. Update - 更新资源

```python
@router.put(
    "/{story_id}",
    response_model=StoryResponse,
    summary="更新小说"
)
async def update_story(
    story_id: str,
    story_update: StoryUpdate,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> StoryResponse:
    """
    更新小说信息
    
    只更新提供的字段，未提供的字段保持不变
    """
    try:
        result = await service.update_story(
            story_id,
            story_update,
            user_id=current_user.id
        )
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Story with id {story_id} not found"
            )
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
```

### 5. Delete - 删除资源

```python
@router.delete(
    "/{story_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="删除小说"
)
async def delete_story(
    story_id: str,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> None:
    """
    删除小说及其所有章节
    
    ⚠️ 此操作不可逆
    """
    success = await service.delete_story(story_id, user_id=current_user.id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Story with id {story_id} not found"
        )
```

---

## SSE 流式输出示例

### 生成章节（流式输出）

```python
from fastapi.responses import StreamingResponse
from typing import AsyncGenerator
import json

@router.post(
    "/{story_id}/chapters/generate",
    summary="生成章节（流式输出）",
    response_class=StreamingResponse
)
async def generate_chapter_stream(
    story_id: str,
    chapter_plan: ChapterPlan,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
):
    """
    流式生成章节内容
    
    使用 Server-Sent Events (SSE) 实时推送生成进度
    """
    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for event in service.generate_chapter_stream(
                story_id,
                chapter_plan,
                user_id=current_user.id
            ):
                # 格式化为 SSE 格式
                data = json.dumps(event, ensure_ascii=False)
                yield f"data: {data}\n\n"
        except Exception as e:
            error_data = json.dumps({"type": "error", "message": str(e)})
            yield f"data: {error_data}\n\n"
        finally:
            # 发送结束信号
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
    
    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no"  # 禁用 nginx 缓冲
        }
    )
```

---

## 嵌套路由示例

### 章节管理（作为小说的子资源）

```python
@router.get(
    "/{story_id}/chapters",
    response_model=List[ChapterResponse],
    summary="获取小说的所有章节"
)
async def list_chapters(
    story_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> List[ChapterResponse]:
    """获取指定小说的章节列表"""
    chapters = await service.list_chapters(
        story_id,
        skip=skip,
        limit=limit,
        user_id=current_user.id
    )
    return chapters


@router.post(
    "/{story_id}/chapters",
    response_model=ChapterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="创建章节"
)
async def create_chapter(
    story_id: str,
    chapter: ChapterCreate,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> ChapterResponse:
    """为指定小说创建新章节"""
    result = await service.create_chapter(
        story_id,
        chapter,
        user_id=current_user.id
    )
    return result


@router.get(
    "/{story_id}/chapters/{chapter_id}",
    response_model=ChapterResponse,
    summary="获取章节详情"
)
async def get_chapter(
    story_id: str,
    chapter_id: str,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
) -> ChapterResponse:
    """获取指定章节的详细内容"""
    chapter = await service.get_chapter(
        story_id,
        chapter_id,
        user_id=current_user.id
    )
    if not chapter:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chapter {chapter_id} not found in story {story_id}"
        )
    return chapter
```

---

## 错误处理

### 自定义异常

```python
class StoryNotFoundError(Exception):
    """小说不存在"""
    pass


class PermissionDeniedError(Exception):
    """权限不足"""
    pass


class ChapterGenerationError(Exception):
    """章节生成失败"""
    pass
```

### 异常处理器

```python
from fastapi import Request
from fastapi.responses import JSONResponse

@router.exception_handler(StoryNotFoundError)
async def story_not_found_handler(request: Request, exc: StoryNotFoundError):
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": str(exc)}
    )


@router.exception_handler(PermissionDeniedError)
async def permission_denied_handler(request: Request, exc: PermissionDeniedError):
    return JSONResponse(
        status_code=status.HTTP_403_FORBIDDEN,
        content={"detail": "You don't have permission to access this resource"}
    )


@router.exception_handler(ChapterGenerationError)
async def chapter_generation_error_handler(request: Request, exc: ChapterGenerationError):
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": f"Chapter generation failed: {str(exc)}"}
    )
```

---

## 中间件示例

### 请求日志中间件

```python
from fastapi import Request
import time
from loguru import logger

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录所有请求"""
    start_time = time.time()
    
    # 记录请求
    logger.info(f"Request: {request.method} {request.url}")
    
    # 处理请求
    response = await call_next(request)
    
    # 记录响应时间
    process_time = time.time() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    logger.info(f"Response: {response.status_code} ({process_time:.3f}s)")
    
    return response
```

---

## 后台任务

### 异步任务示例

```python
from fastapi import BackgroundTasks

def send_notification(user_id: str, message: str):
    """发送通知（后台任务）"""
    # 发送邮件/推送通知等
    logger.info(f"Sending notification to user {user_id}: {message}")


@router.post("/{story_id}/publish")
async def publish_story(
    story_id: str,
    background_tasks: BackgroundTasks,
    service: StoryService = Depends(get_story_service),
    current_user: User = Depends(get_current_user)
):
    """发布小说"""
    story = await service.publish_story(story_id, user_id=current_user.id)
    
    # 添加后台任务
    background_tasks.add_task(
        send_notification,
        user_id=current_user.id,
        message=f"Your story '{story.title}' has been published!"
    )
    
    return {"message": "Story published successfully"}
```

---

## 请求验证

### Pydantic 模型验证

```python
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class StoryCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=200, description="小说标题")
    description: Optional[str] = Field(None, max_length=2000, description="小说简介")
    genre: str = Field(..., description="题材类型")
    tags: List[str] = Field(default_factory=list, description="标签列表")
    
    @validator("title")
    def title_must_not_be_empty(cls, v):
        if not v.strip():
            raise ValueError("Title cannot be empty")
        return v.strip()
    
    @validator("tags")
    def validate_tags(cls, v):
        if len(v) > 10:
            raise ValueError("Too many tags (max 10)")
        return v
    
    class Config:
        schema_extra = {
            "example": {
                "title": "重生之我是修仙大佬",
                "description": "一个现代人穿越到修仙世界的故事",
                "genre": "玄幻",
                "tags": ["穿越", "修仙", "系统流"]
            }
        }
```

---

## 认证和授权

### JWT 认证

```python
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt

security = HTTPBearer()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> User:
    """从 JWT token 获取当前用户"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials"
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
        )
    
    # 从数据库获取用户
    user = await get_user_by_id(db, user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    return user
```

---

## 完整路由注册

```python
# main.py
from fastapi import FastAPI
from .api import stories, chapters, users

app = FastAPI(
    title="DreamWeaver API",
    description="Multi-Agent 长篇小说创作系统 API",
    version="1.0.0"
)

# 注册路由
app.include_router(stories.router)
app.include_router(chapters.router)
app.include_router(users.router)

# 健康检查
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
```
