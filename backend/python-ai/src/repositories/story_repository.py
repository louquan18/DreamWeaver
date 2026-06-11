"""小说 Repository"""

import uuid
from typing import Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.story import Story
from src.schemas.story import StoryCreate, StoryUpdate


class StoryRepository:
    """小说数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(self, data: StoryCreate, user_id: uuid.UUID) -> Story:
        story = Story(**data.model_dump(), user_id=user_id)
        self.db.add(story)
        await self.db.commit()
        await self.db.refresh(story)
        return story

    async def get_by_id(self, story_id: uuid.UUID) -> Optional[Story]:
        result = await self.db.execute(
            select(Story).where(Story.id == story_id)
        )
        return result.scalar_one_or_none()

    async def list(
        self,
        user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Story]:
        query = select(Story)
        if user_id:
            query = query.where(Story.user_id == user_id)
        query = query.order_by(Story.created_at.desc()).offset(skip).limit(limit)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def update(self, story_id: uuid.UUID, data: StoryUpdate) -> Optional[Story]:
        update_data = data.model_dump(exclude_unset=True)
        if not update_data:
            return await self.get_by_id(story_id)

        from sqlalchemy import update

        await self.db.execute(
            update(Story).where(Story.id == story_id).values(**update_data)
        )
        await self.db.commit()
        return await self.get_by_id(story_id)

    async def delete(self, story_id: uuid.UUID) -> bool:
        from sqlalchemy import delete

        result = await self.db.execute(
            delete(Story).where(Story.id == story_id)
        )
        await self.db.commit()
        return result.rowcount > 0

    async def count(self, user_id: Optional[uuid.UUID] = None) -> int:
        query = select(func.count()).select_from(Story)
        if user_id:
            query = query.where(Story.user_id == user_id)
        result = await self.db.execute(query)
        return result.scalar()
