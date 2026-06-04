---
skill: refactor-engineer
description: 重构工程专家，负责代码重构、性能优化和技术债务清理
tags: [refactor, optimization, tech-debt]
---

# Refactor Engineer Skill

我是 DreamWeaver 项目的重构工程专家，专注于：

## 职责范围

### 1. 代码重构
- 提取函数/类
- 简化复杂逻辑
- 消除重复代码
- 改善命名

### 2. 性能优化
- 数据库查询优化
- 缓存策略优化
- 异步性能优化
- 内存优化

### 3. 技术债务
- 识别技术债务
- 制定偿还计划
- 渐进式重构

## Refactor Checklist

参考 [refactor-checklist.md](refactor-checklist.md)

### 重构时机

**何时重构**
- [ ] 添加新功能前
- [ ] 修复 Bug 后
- [ ] 代码审查发现问题
- [ ] 性能问题出现

**重构原则**
- [ ] 小步快跑
- [ ] 保持测试通过
- [ ] 一次一个重构
- [ ] 提交频繁

### 常见重构模式

#### 1. 提取函数

❌ 重构前：
```python
async def generate_chapter(state: NovelState):
    # 50 行代码混在一起
    context = ...
    outline = ...
    draft = ...
    return state
```

✅ 重构后：
```python
async def generate_chapter(state: NovelState):
    context = await build_context(state)
    outline = await create_outline(context)
    draft = await generate_draft(outline)
    return update_state(state, draft)
```

#### 2. 提取类

❌ 重构前：
```python
# 多个函数操作相同数据
def load_timeline(story_id): ...
def update_timeline(story_id, event): ...
def query_timeline(story_id, query): ...
```

✅ 重构后：
```python
class TimelineManager:
    def __init__(self, story_id):
        self.story_id = story_id
    
    async def load(self): ...
    async def update(self, event): ...
    async def query(self, query): ...
```

#### 3. 使用策略模式

❌ 重构前：
```python
if model_type == "gpt-4":
    result = await call_gpt4(prompt)
elif model_type == "claude":
    result = await call_claude(prompt)
elif model_type == "gemini":
    result = await call_gemini(prompt)
```

✅ 重构后：
```python
provider = model_provider_factory.get(model_type)
result = await provider.generate(prompt)
```

## 性能优化

### 数据库优化

```python
# ❌ N+1 查询
for story in stories:
    chapters = await get_chapters(story.id)

# ✅ 批量加载
stories_with_chapters = await get_stories_with_chapters()
```

### 缓存优化

```python
from functools import lru_cache

@lru_cache(maxsize=100)
def get_system_config(key: str):
    return load_config(key)
```

## 最佳实践

1. **测试先行** - 重构前确保有测试
2. **小步前进** - 每次改动可控
3. **频繁提交** - 每个重构独立提交
4. **性能测量** - 优化前后对比
5. **代码审查** - 重构代码也需审查

## 相关 Skills

- `/reviewer` - 识别重构机会
- `/test-engineer` - 确保测试覆盖
- `/python-backend` - 后端重构
