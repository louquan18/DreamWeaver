"""章节 Pydantic 模型"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class ChapterCreate(BaseModel):
    """创建章节请求"""

    chapter_number: int = Field(..., ge=1, description="章节序号")
    title: Optional[str] = Field(None, max_length=200, description="章节标题")


class ChapterUpdate(BaseModel):
    """更新章节请求（部分更新）"""

    title: Optional[str] = Field(None, max_length=200)
    content_url: Optional[str] = None
    word_count: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=20)


class ChapterResponse(BaseModel):
    """章节响应"""

    id: uuid.UUID
    story_id: uuid.UUID
    chapter_number: int
    title: Optional[str] = None
    content: Optional[str] = None
    content_url: Optional[str] = None
    word_count: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
