"""小说 CRUD API"""

import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.database import get_db
from src.repositories.story_repository import StoryRepository
from src.repositories.chapter_repository import ChapterRepository
from src.schemas.story import StoryCreate, StoryResponse, StoryUpdate
from src.schemas.chapter import ChapterCreate, ChapterResponse

router = APIRouter(prefix="/api/stories", tags=["stories"])


def _get_repo(db: AsyncSession = Depends(get_db)) -> StoryRepository:
    return StoryRepository(db)


def _get_chapter_repo(db: AsyncSession = Depends(get_db)) -> ChapterRepository:
    return ChapterRepository(db)


@router.post("", response_model=StoryResponse, status_code=status.HTTP_201_CREATED)
async def create_story(data: StoryCreate, repo: StoryRepository = Depends(_get_repo)):
    """创建小说"""
    # 使用固定的 user_id（暂无认证）
    user_id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    story = await repo.create(data, user_id)
    return story


@router.get("", response_model=list[StoryResponse])
async def list_stories(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    repo: StoryRepository = Depends(_get_repo),
):
    """列出小说"""
    return await repo.list(skip=skip, limit=limit)


@router.get("/{story_id}", response_model=StoryResponse)
async def get_story(story_id: uuid.UUID, repo: StoryRepository = Depends(_get_repo)):
    """获取小说详情"""
    story = await repo.get_by_id(story_id)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.put("/{story_id}", response_model=StoryResponse)
async def update_story(
    story_id: uuid.UUID,
    data: StoryUpdate,
    repo: StoryRepository = Depends(_get_repo),
):
    """更新小说"""
    story = await repo.update(story_id, data)
    if not story:
        raise HTTPException(status_code=404, detail="Story not found")
    return story


@router.delete("/{story_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_story(story_id: uuid.UUID, repo: StoryRepository = Depends(_get_repo)):
    """删除小说"""
    if not await repo.delete(story_id):
        raise HTTPException(status_code=404, detail="Story not found")


# ========== 章节子资源 ==========


@router.post("/{story_id}/chapters", response_model=ChapterResponse, status_code=status.HTTP_201_CREATED)
async def create_chapter(
    story_id: uuid.UUID,
    data: ChapterCreate,
    chapter_repo: ChapterRepository = Depends(_get_chapter_repo),
    story_repo: StoryRepository = Depends(_get_repo),
):
    """为小说创建章节"""
    if not await story_repo.get_by_id(story_id):
        raise HTTPException(status_code=404, detail="Story not found")
    return await chapter_repo.create(data, story_id)


@router.get("/{story_id}/chapters", response_model=list[ChapterResponse])
async def list_chapters(
    story_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    chapter_repo: ChapterRepository = Depends(_get_chapter_repo),
):
    """列出小说的所有章节"""
    return await chapter_repo.list_by_story(story_id, skip=skip, limit=limit)


@router.get("/{story_id}/chapters/{chapter_id}", response_model=ChapterResponse)
async def get_chapter(
    story_id: uuid.UUID,
    chapter_id: uuid.UUID,
    chapter_repo: ChapterRepository = Depends(_get_chapter_repo),
):
    """获取章节详情"""
    chapter = await chapter_repo.get_by_id(chapter_id)
    if not chapter or chapter.story_id != story_id:
        raise HTTPException(status_code=404, detail="Chapter not found")
    return chapter
