# Repository 模式模板

## 什么是 Repository 模式？

Repository 模式是数据访问层的抽象，它提供了一个类似集合的接口来访问领域对象。

**优点**：
- 解耦业务逻辑和数据访问
- 便于单元测试（可 Mock）
- 统一数据访问接口
- 易于切换数据源

---

## 基础 Repository 接口

```python
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """基础 Repository 抽象类"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """创建实体"""
        pass
    
    @abstractmethod
    async def get_by_id(self, entity_id: str) -> Optional[T]:
        """根据 ID 获取实体"""
        pass
    
    @abstractmethod
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        **filters
    ) -> List[T]:
        """列出实体（支持分页和筛选）"""
        pass
    
    @abstractmethod
    async def update(self, entity_id: str, data: dict) -> Optional[T]:
        """更新实体"""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: str) -> bool:
        """删除实体"""
        pass
    
    @abstractmethod
    async def exists(self, entity_id: str) -> bool:
        """检查实体是否存在"""
        pass
```

---

## Story Repository 实现示例

```python
from sqlalchemy import select, update, delete, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from ..models.story import Story
from ..schemas.story import StoryCreate, StoryUpdate

class StoryRepository(BaseRepository[Story]):
    """小说 Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
    
    async def create(self, story_data: StoryCreate, user_id: str) -> Story:
        """
        创建小说
        
        Args:
            story_data: 小说数据
            user_id: 用户 ID
            
        Returns:
            Story: 创建的小说对象
        """
        story = Story(
            **story_data.dict(),
            user_id=user_id
        )
        self.db.add(story)
        await self.db.commit()
        await self.db.refresh(story)
        return story
    
    async def get_by_id(self, story_id: str) -> Optional[Story]:
        """
        根据 ID 获取小说
        
        Args:
            story_id: 小说 ID
            
        Returns:
            Optional[Story]: 小说对象或 None
        """
        result = await self.db.execute(
            select(Story).where(Story.id == story_id)
        )
        return result.scalar_one_or_none()
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        user_id: Optional[str] = None,
        genre: Optional[str] = None,
        search: Optional[str] = None
    ) -> List[Story]:
        """
        列出小说
        
        Args:
            skip: 跳过的记录数
            limit: 返回的最大记录数
            user_id: 按用户 ID 筛选
            genre: 按题材筛选
            search: 搜索关键词
            
        Returns:
            List[Story]: 小说列表
        """
        query = select(Story)
        
        # 添加筛选条件
        if user_id:
            query = query.where(Story.user_id == user_id)
        if genre:
            query = query.where(Story.genre == genre)
        if search:
            query = query.where(
                Story.title.ilike(f"%{search}%") | 
                Story.description.ilike(f"%{search}%")
            )
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        # 排序
        query = query.order_by(Story.created_at.desc())
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        story_id: str,
        story_update: StoryUpdate
    ) -> Optional[Story]:
        """
        更新小说
        
        Args:
            story_id: 小说 ID
            story_update: 更新数据
            
        Returns:
            Optional[Story]: 更新后的小说对象或 None
        """
        # 只更新提供的字段
        update_data = story_update.dict(exclude_unset=True)
        
        if not update_data:
            return await self.get_by_id(story_id)
        
        await self.db.execute(
            update(Story)
            .where(Story.id == story_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_by_id(story_id)
    
    async def delete(self, story_id: str) -> bool:
        """
        删除小说
        
        Args:
            story_id: 小说 ID
            
        Returns:
            bool: 是否删除成功
        """
        result = await self.db.execute(
            delete(Story).where(Story.id == story_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def exists(self, story_id: str) -> bool:
        """
        检查小说是否存在
        
        Args:
            story_id: 小说 ID
            
        Returns:
            bool: 是否存在
        """
        result = await self.db.execute(
            select(func.count()).select_from(Story).where(Story.id == story_id)
        )
        count = result.scalar()
        return count > 0
    
    async def get_by_user(self, user_id: str) -> List[Story]:
        """
        获取用户的所有小说
        
        Args:
            user_id: 用户 ID
            
        Returns:
            List[Story]: 小说列表
        """
        result = await self.db.execute(
            select(Story)
            .where(Story.user_id == user_id)
            .order_by(Story.created_at.desc())
        )
        return result.scalars().all()
    
    async def count(self, user_id: Optional[str] = None) -> int:
        """
        统计小说数量
        
        Args:
            user_id: 按用户 ID 筛选（可选）
            
        Returns:
            int: 小说数量
        """
        query = select(func.count()).select_from(Story)
        
        if user_id:
            query = query.where(Story.user_id == user_id)
        
        result = await self.db.execute(query)
        return result.scalar()
```

---

## Chapter Repository 实现示例

```python
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from ..models.chapter import Chapter
from ..schemas.chapter import ChapterCreate, ChapterUpdate

class ChapterRepository(BaseRepository[Chapter]):
    """章节 Repository"""
    
    def __init__(self, db: AsyncSession):
        super().__init__(db)
    
    async def create(
        self,
        chapter_data: ChapterCreate,
        story_id: str
    ) -> Chapter:
        """创建章节"""
        chapter = Chapter(
            **chapter_data.dict(),
            story_id=story_id
        )
        self.db.add(chapter)
        await self.db.commit()
        await self.db.refresh(chapter)
        return chapter
    
    async def get_by_id(self, chapter_id: str) -> Optional[Chapter]:
        """根据 ID 获取章节"""
        result = await self.db.execute(
            select(Chapter).where(Chapter.id == chapter_id)
        )
        return result.scalar_one_or_none()
    
    async def list(
        self,
        skip: int = 0,
        limit: int = 100,
        story_id: Optional[str] = None
    ) -> List[Chapter]:
        """列出章节"""
        query = select(Chapter)
        
        if story_id:
            query = query.where(Chapter.story_id == story_id)
        
        query = query.order_by(Chapter.chapter_number).offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update(
        self,
        chapter_id: str,
        chapter_update: ChapterUpdate
    ) -> Optional[Chapter]:
        """更新章节"""
        update_data = chapter_update.dict(exclude_unset=True)
        
        if not update_data:
            return await self.get_by_id(chapter_id)
        
        await self.db.execute(
            update(Chapter)
            .where(Chapter.id == chapter_id)
            .values(**update_data)
        )
        await self.db.commit()
        
        return await self.get_by_id(chapter_id)
    
    async def delete(self, chapter_id: str) -> bool:
        """删除章节"""
        result = await self.db.execute(
            delete(Chapter).where(Chapter.id == chapter_id)
        )
        await self.db.commit()
        return result.rowcount > 0
    
    async def exists(self, chapter_id: str) -> bool:
        """检查章节是否存在"""
        result = await self.db.execute(
            select(func.count()).select_from(Chapter).where(Chapter.id == chapter_id)
        )
        return result.scalar() > 0
    
    async def get_by_story(self, story_id: str) -> List[Chapter]:
        """获取小说的所有章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(Chapter.story_id == story_id)
            .order_by(Chapter.chapter_number)
        )
        return result.scalars().all()
    
    async def get_latest_chapter(self, story_id: str) -> Optional[Chapter]:
        """获取最新章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(Chapter.story_id == story_id)
            .order_by(Chapter.chapter_number.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()
    
    async def get_chapter_by_number(
        self,
        story_id: str,
        chapter_number: int
    ) -> Optional[Chapter]:
        """根据章节号获取章节"""
        result = await self.db.execute(
            select(Chapter)
            .where(
                Chapter.story_id == story_id,
                Chapter.chapter_number == chapter_number
            )
        )
        return result.scalar_one_or_none()
```

---

## 事务管理示例

```python
from contextlib import asynccontextmanager

class StoryService:
    """小说服务"""
    
    def __init__(
        self,
        story_repo: StoryRepository,
        chapter_repo: ChapterRepository
    ):
        self.story_repo = story_repo
        self.chapter_repo = chapter_repo
    
    async def create_story_with_chapters(
        self,
        story_data: StoryCreate,
        chapters_data: List[ChapterCreate],
        user_id: str
    ) -> Story:
        """
        创建小说及其章节（事务）
        
        使用事务确保要么全部成功，要么全部回滚
        """
        async with self.story_repo.db.begin():
            # 创建小说
            story = await self.story_repo.create(story_data, user_id)
            
            # 创建章节
            for chapter_data in chapters_data:
                await self.chapter_repo.create(chapter_data, story.id)
            
            # 提交事务
            await self.story_repo.db.commit()
            
        return story
```

---

## 批量操作示例

```python
class ChapterRepository(BaseRepository[Chapter]):
    
    async def bulk_create(
        self,
        chapters_data: List[ChapterCreate],
        story_id: str
    ) -> List[Chapter]:
        """批量创建章节"""
        chapters = [
            Chapter(**chapter_data.dict(), story_id=story_id)
            for chapter_data in chapters_data
        ]
        
        self.db.add_all(chapters)
        await self.db.commit()
        
        # 刷新所有对象
        for chapter in chapters:
            await self.db.refresh(chapter)
        
        return chapters
    
    async def bulk_update_status(
        self,
        chapter_ids: List[str],
        status: str
    ) -> int:
        """批量更新章节状态"""
        result = await self.db.execute(
            update(Chapter)
            .where(Chapter.id.in_(chapter_ids))
            .values(status=status)
        )
        await self.db.commit()
        return result.rowcount
```

---

## 复杂查询示例

```python
from sqlalchemy import and_, or_

class StoryRepository(BaseRepository[Story]):
    
    async def search_advanced(
        self,
        keyword: Optional[str] = None,
        genres: Optional[List[str]] = None,
        min_chapters: Optional[int] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 100
    ) -> List[Story]:
        """
        高级搜索
        
        支持多条件组合查询
        """
        query = select(Story)
        
        conditions = []
        
        # 关键词搜索
        if keyword:
            conditions.append(
                or_(
                    Story.title.ilike(f"%{keyword}%"),
                    Story.description.ilike(f"%{keyword}%")
                )
            )
        
        # 题材筛选
        if genres:
            conditions.append(Story.genre.in_(genres))
        
        # 最小章节数
        if min_chapters is not None:
            conditions.append(Story.chapter_count >= min_chapters)
        
        # 状态筛选
        if status:
            conditions.append(Story.status == status)
        
        if conditions:
            query = query.where(and_(*conditions))
        
        # 分页
        query = query.offset(skip).limit(limit)
        
        result = await self.db.execute(query)
        return result.scalars().all()
```

---

## 关联查询示例

```python
from sqlalchemy.orm import selectinload, joinedload

class StoryRepository(BaseRepository[Story]):
    
    async def get_with_chapters(self, story_id: str) -> Optional[Story]:
        """
        获取小说及其所有章节（预加载）
        
        使用 selectinload 避免 N+1 查询问题
        """
        result = await self.db.execute(
            select(Story)
            .options(selectinload(Story.chapters))
            .where(Story.id == story_id)
        )
        return result.scalar_one_or_none()
    
    async def get_with_user(self, story_id: str) -> Optional[Story]:
        """
        获取小说及其作者信息（关联查询）
        
        使用 joinedload 一次性获取关联数据
        """
        result = await self.db.execute(
            select(Story)
            .options(joinedload(Story.user))
            .where(Story.id == story_id)
        )
        return result.scalar_one_or_none()
```

---

## 分页辅助类

```python
from pydantic import BaseModel
from typing import Generic, TypeVar, List

T = TypeVar('T')

class Page(BaseModel, Generic[T]):
    """分页结果"""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    @classmethod
    def create(
        cls,
        items: List[T],
        total: int,
        page: int,
        page_size: int
    ) -> "Page[T]":
        """创建分页对象"""
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=(total + page_size - 1) // page_size
        )

class StoryRepository(BaseRepository[Story]):
    
    async def paginate(
        self,
        page: int = 1,
        page_size: int = 20,
        **filters
    ) -> Page[Story]:
        """分页查询"""
        # 计算 skip
        skip = (page - 1) * page_size
        
        # 获取数据
        items = await self.list(skip=skip, limit=page_size, **filters)
        
        # 获取总数
        total = await self.count(**filters)
        
        return Page.create(
            items=items,
            total=total,
            page=page,
            page_size=page_size
        )
```

---

## 测试 Repository

```python
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

@pytest.mark.asyncio
async def test_create_story(db: AsyncSession):
    """测试创建小说"""
    repo = StoryRepository(db)
    
    story_data = StoryCreate(
        title="测试小说",
        description="这是一篇测试小说",
        genre="玄幻"
    )
    
    story = await repo.create(story_data, user_id="user-123")
    
    assert story.id is not None
    assert story.title == "测试小说"
    assert story.user_id == "user-123"


@pytest.mark.asyncio
async def test_get_story(db: AsyncSession):
    """测试获取小说"""
    repo = StoryRepository(db)
    
    # 先创建
    story = await repo.create(
        StoryCreate(title="测试", genre="玄幻"),
        user_id="user-123"
    )
    
    # 再获取
    fetched = await repo.get_by_id(story.id)
    
    assert fetched is not None
    assert fetched.id == story.id
    assert fetched.title == "测试"
```

---

## 最佳实践

1. **Repository 只负责数据访问** - 不包含业务逻辑
2. **使用类型提示** - 提高代码可读性
3. **异步操作** - 所有数据库操作使用 async/await
4. **事务管理** - 复杂操作使用事务确保一致性
5. **避免 N+1 查询** - 使用 selectinload/joinedload 预加载关联数据
6. **错误处理** - 捕获并转换数据库异常
7. **测试覆盖** - 为每个 Repository 方法编写测试
