---
skill: novel-skill-engineer
description: 小说技能工程专家，负责网文题材分析、伏笔设计和人物关系图构建
tags: [novel, genre-analysis, foreshadow, character-graph]
---

# Novel Skill Engineer Skill

我是 DreamWeaver 项目的小说技能工程专家，专注于：

## 职责范围

### 1. 题材分析
- 网文题材分类
- 套路识别
- 结构分析
- 范本学习

### 2. 伏笔设计
- 伏笔埋设策略
- 触发条件设计
- 回收时机规划
- 伏笔追踪

### 3. 人物关系图
- 人物关系建模
- 关系演化追踪
- 冲突设计
- 性格一致性

## 题材分析

参考 [genre-analysis.md](genre-analysis.md)

### 常见网文题材

**玄幻修仙**
- 修炼体系：炼气 → 筑基 → 金丹 → 元婴
- 常见套路：穿越、重生、系统流
- 节奏：快节奏升级，频繁战斗

**都市重生**
- 核心：利用重生优势改变命运
- 常见元素：商战、投资、复仇
- 节奏：稳扎稳打，逐步布局

**系统流**
- 核心：系统辅助主角成长
- 常见功能：任务、商城、签到
- 节奏：任务驱动，节奏紧凑

## 伏笔设计

参考 [foreshadow-design.md](foreshadow-design.md)

### 伏笔类型

**1. 道具伏笔**
```python
foreshadow = {
    "type": "item",
    "content": "主角获得破损的古老令牌",
    "planted_chapter": 15,
    "trigger_condition": "主角达到元婴期",
    "resolution": "令牌指引主角找到上古秘境",
    "importance": "high"
}
```

**2. 人物伏笔**
```python
foreshadow = {
    "type": "character",
    "content": "神秘老人提到主角身世",
    "planted_chapter": 20,
    "trigger_condition": "主角遇到血族",
    "resolution": "揭示主角真实身份",
    "importance": "high"
}
```

**3. 事件伏笔**
```python
foreshadow = {
    "type": "event",
    "content": "魔教蠢蠢欲动",
    "planted_chapter": 30,
    "trigger_condition": "天元大会召开",
    "resolution": "魔教突袭天元大会",
    "importance": "medium"
}
```

### 伏笔管理

```python
class ForeshadowManager:
    """伏笔管理器"""
    
    async def plant_foreshadow(self, foreshadow: Foreshadow):
        """埋设伏笔"""
        await self.db.save(foreshadow)
    
    async def check_triggers(self, current_state: Dict):
        """检查哪些伏笔可以触发"""
        active = await self.db.get_active_foreshadows()
        
        triggered = []
        for f in active:
            if self.should_trigger(f, current_state):
                triggered.append(f)
        
        return triggered
    
    async def resolve_foreshadow(self, foreshadow_id: str):
        """回收伏笔"""
        await self.db.update(foreshadow_id, status="resolved")
```

## 人物关系图

参考 [character-graph.md](character-graph.md)

### 关系建模

```python
class CharacterGraph:
    """人物关系图"""
    
    def __init__(self):
        self.graph = nx.DiGraph()
    
    def add_character(self, name: str, attributes: Dict):
        """添加人物"""
        self.graph.add_node(name, **attributes)
    
    def add_relationship(
        self,
        from_char: str,
        to_char: str,
        rel_type: str,
        strength: int
    ):
        """添加关系"""
        self.graph.add_edge(
            from_char,
            to_char,
            type=rel_type,
            strength=strength
        )
    
    def get_relationships(self, char_name: str):
        """获取人物关系"""
        return list(self.graph.edges(char_name, data=True))
    
    def find_conflicts(self):
        """发现潜在冲突"""
        conflicts = []
        for node in self.graph.nodes():
            enemies = [
                e for e in self.graph.edges(node, data=True)
                if e[2]['type'] == 'enemy'
            ]
            conflicts.extend(enemies)
        return conflicts
```

### 关系演化

```python
async def update_relationship(
    char_a: str,
    char_b: str,
    event: str
):
    """根据事件更新关系"""
    
    current_rel = graph.get_edge(char_a, char_b)
    
    # 根据事件类型调整关系
    if event == "帮助":
        current_rel['strength'] += 10
    elif event == "背叛":
        current_rel['strength'] -= 50
        current_rel['type'] = 'enemy'
    
    graph.update_edge(char_a, char_b, current_rel)
```

## 小说技能库

### 语料蒸馏

```python
async def distill_novel(novel_text: str):
    """蒸馏小说语料"""
    
    # 1. 文本清洗
    cleaned = clean_text(novel_text)
    
    # 2. 生成摘要
    summary = await generate_summary(cleaned)
    
    # 3. 提取标签
    tags = await extract_tags(cleaned)
    
    # 4. 结构抽取
    structure = await extract_structure(cleaned)
    
    # 5. 向量化
    embedding = await create_embedding(summary)
    
    return {
        "summary": summary,
        "tags": tags,
        "structure": structure,
        "embedding": embedding
    }
```

## 最佳实践

1. **题材匹配** - 根据题材选择合适套路
2. **伏笔密度** - 每 10 章埋设 1-2 个伏笔
3. **关系复杂度** - 主要人物关系清晰
4. **冲突设计** - 多层次冲突交织
5. **节奏控制** - 张弛有度

## 相关 Skills

- `/context-engineer` - 记忆系统集成
- `/langgraph-architect` - Agent 集成
