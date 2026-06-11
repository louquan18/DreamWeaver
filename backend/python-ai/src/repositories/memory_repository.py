"""记忆 Repository - 结构化记忆的数据库 CRUD"""

import uuid
from typing import Any

from sqlalchemy import select, delete, and_
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.story_memory import StoryMemory


class MemoryRepository:
    """结构化记忆数据访问层"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def save_memory(
        self,
        story_id: uuid.UUID,
        memory_type: str,
        content: dict[str, Any],
        chapter_range: list[int] | None = None,
    ) -> StoryMemory:
        """保存一条记忆记录"""
        memory = StoryMemory(
            story_id=story_id,
            memory_type=memory_type,
            content=content,
            chapter_range=chapter_range,
        )
        self.db.add(memory)
        await self.db.commit()
        await self.db.refresh(memory)
        return memory

    async def get_memories(
        self,
        story_id: uuid.UUID,
        memory_type: str | None = None,
    ) -> list[StoryMemory]:
        """获取记忆列表"""
        query = select(StoryMemory).where(StoryMemory.story_id == story_id)
        if memory_type:
            query = query.where(StoryMemory.memory_type == memory_type)
        query = query.order_by(StoryMemory.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_latest_memory(
        self,
        story_id: uuid.UUID,
        memory_type: str,
    ) -> StoryMemory | None:
        """获取指定类型的最新记忆"""
        query = (
            select(StoryMemory)
            .where(
                and_(
                    StoryMemory.story_id == story_id,
                    StoryMemory.memory_type == memory_type,
                )
            )
            .order_by(StoryMemory.created_at.desc())
            .limit(1)
        )
        result = await self.db.execute(query)
        return result.scalar_one_or_none()

    async def update_memory(
        self,
        memory_id: uuid.UUID,
        content: dict[str, Any],
    ) -> StoryMemory | None:
        """更新记忆内容"""
        from sqlalchemy import update

        await self.db.execute(
            update(StoryMemory)
            .where(StoryMemory.id == memory_id)
            .values(content=content)
        )
        await self.db.commit()

        result = await self.db.execute(
            select(StoryMemory).where(StoryMemory.id == memory_id)
        )
        return result.scalar_one_or_none()

    async def delete_memories(
        self,
        story_id: uuid.UUID,
        memory_type: str | None = None,
    ) -> int:
        """删除记忆"""
        query = delete(StoryMemory).where(StoryMemory.story_id == story_id)
        if memory_type:
            query = query.where(StoryMemory.memory_type == memory_type)

        result = await self.db.execute(query)
        await self.db.commit()
        return result.rowcount
