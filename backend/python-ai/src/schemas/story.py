"""小说 Pydantic 模型"""

import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class StoryCreate(BaseModel):
    """创建小说请求"""

    title: str = Field(..., min_length=1, max_length=200, description="小说标题")
    description: Optional[str] = Field(None, max_length=5000, description="小说简介")
    genre: Optional[str] = Field(None, max_length=50, description="题材类型（玄幻/都市/科幻等）")
    target_words: Optional[int] = Field(None, ge=0, description="目标字数")


class StoryUpdate(BaseModel):
    """更新小说请求（部分更新）"""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=5000)
    genre: Optional[str] = Field(None, max_length=50)
    target_words: Optional[int] = Field(None, ge=0)
    status: Optional[str] = Field(None, max_length=20)


class StoryResponse(BaseModel):
    """小说响应"""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    description: Optional[str] = None
    genre: Optional[str] = None
    target_words: Optional[int] = None
    status: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
