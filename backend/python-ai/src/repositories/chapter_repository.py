"""章节 Repository"""

import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.chapter import Chapter
from src.schemas.chapter import ChapterCreate, ChapterUpdate


class ChapterRepository:
    """章节数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: ChapterCreate, story_id: uuid.UUID) -> Chapter:
        chapter = Chapter(**data.model_dump(), story_id=story_id)
        self.db.add(chapter)
        await self.db.commit()
        await self.db.refresh(chapter)
        return chapter

    async def get_by_id(self, chapter_id: uuid.UUID) -> Optional[Chapter]:
        result = await self.db.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        return result.scalar_one_or_none()

    async def list_by_story(
        self,
        story_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Chapter]:
        query = (
            select(Chapter)
            .where(Chapter.story_id == story_id)
            .order_by(Chapter.chapter_number)
            .offset(skip)
            .limit(limit)
        )
        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest(self, story_id: uuid.UUID) -> Optional[Chapter]:
        query = (
            select(Chapter)
            .where(Chapter.story_id == story_id)
            .order_by(Chapter.chapter_number.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update(self, chapter_id: uuid.UUID, data: ChapterUpdate) -> Optional[Chapter]:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(chapter_id)

        from sqlalchemy import update

        await self.db.execute(
            update(Chapter).where(Chapter.id == chapter_id).values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(chapter_id)

    async def delete(self, chapter_id: uuid.UUID) -> bool:
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(Chapter).where(Chapter.id == chapter_id)
        )
        await self.db.commit()
        return result.rowcount > 0
