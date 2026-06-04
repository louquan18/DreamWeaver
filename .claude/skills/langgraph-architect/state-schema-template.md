# State Schema 模板

## NovelState - 小说创作工作流状态

```python
from typing import TypedDict, Optional, List, Dict, Any
from datetime import datetime

class NovelState(TypedDict, total=False):
    """
    小说创作工作流状态定义
    
    使用 TypedDict 定义状态结构，LangGraph 会自动管理状态传递
    """
    
    # ========== 基础信息 ==========
    story_id: str
    """小说 ID"""
    
    chapter_id: str
    """章节 ID"""
    
    user_id: str
    """用户 ID"""
    
    # ========== 上下文信息 ==========
    novel_context: Dict[str, Any]
    """
    小说上下文
    
    包含：
    - recent_chapters: 最近章节列表
    - characters: 人物状态
    - timeline: 时间线
    - world_state: 世界观状态
    - foreshadows: 活跃伏笔
    """
    
    chapter_outline: Dict[str, Any]
    """
    章节大纲
    
    包含：
    - goal: 章节目标
    - conflict: 主要冲突
    - plot_points: 关键情节点
    - estimated_words: 预估字数
    """
    
    # ========== 生成内容 ==========
    generated_draft: str
    """生成的章节草稿"""
    
    # ========== 检查报告 ==========
    consistency_report: Dict[str, Any]
    """
    一致性检查报告
    
    包含：
    - character_issues: 人物一致性问题
    - world_issues: 世界观一致性问题
    - plot_issues: 情节一致性问题
    - total_issues: 总问题数
    """
    
    review_report: Dict[str, Any]
    """
    评审报告
    
    包含：
    - score: 总体评分 (0-100)
    - language_quality: 语言质量评分
    - rhythm_control: 节奏控制评分
    - conflict_intensity: 冲突强度评分
    - suggestions: 修改建议
    """
    
    # ========== 执行状态 ==========
    execution_history: List[str]
    """
    执行历史
    
    记录已执行的节点名称，用于追踪工作流进度
    """
    
    current_node: Optional[str]
    """当前正在执行的节点"""
    
    # ========== Checkpoint 相关 ==========
    checkpoint_id: Optional[str]
    """Checkpoint ID"""
    
    checkpoint_timestamp: Optional[datetime]
    """Checkpoint 时间戳"""
    
    # ========== 错误处理 ==========
    error: Optional[str]
    """错误信息（如果有）"""
    
    retry_count: int
    """重试次数"""
    
    # ========== 元数据 ==========
    metadata: Dict[str, Any]
    """
    元数据
    
    可用于存储额外信息，如：
    - model_name: 使用的模型
    - tokens_used: 使用的 Token 数
    - execution_time: 执行时间
    """
```

---

## 状态初始化示例

```python
def create_initial_state(
    story_id: str,
    chapter_id: str,
    user_id: str
) -> NovelState:
    """创建初始状态"""
    return NovelState(
        story_id=story_id,
        chapter_id=chapter_id,
        user_id=user_id,
        novel_context={},
        chapter_outline={},
        generated_draft="",
        consistency_report={},
        review_report={},
        execution_history=[],
        current_node=None,
        checkpoint_id=None,
        checkpoint_timestamp=None,
        error=None,
        retry_count=0,
        metadata={}
    )
```

---

## 状态更新模式

### 1. 简单字段更新

```python
async def update_node(state: NovelState) -> NovelState:
    """更新节点示例"""
    # 创建新状态（不修改原状态）
    new_state = state.copy()
    
    # 更新字段
    new_state["current_node"] = "update_node"
    new_state["execution_history"].append("update_node")
    
    return new_state
```

### 2. 复杂对象更新

```python
async def context_node(state: NovelState) -> NovelState:
    """上下文节点"""
    # 构建上下文
    context = {
        "recent_chapters": await load_recent_chapters(state["story_id"]),
        "characters": await load_characters(state["story_id"]),
        "timeline": await build_timeline(state["story_id"]),
        "world_state": await load_world_state(state["story_id"]),
        "foreshadows": await load_foreshadows(state["story_id"])
    }
    
    # 更新状态
    new_state = state.copy()
    new_state["novel_context"] = context
    new_state["execution_history"].append("novel_context")
    
    return new_state
```

### 3. 部分更新

```python
async def partial_update_node(state: NovelState) -> Dict[str, Any]:
    """
    部分更新
    
    LangGraph 支持返回部分状态，会自动合并到完整状态中
    """
    return {
        "current_node": "partial_update_node",
        "execution_history": state["execution_history"] + ["partial_update_node"]
    }
```

---

## 状态验证

```python
from pydantic import BaseModel, validator

class NovelStateValidator(BaseModel):
    """状态验证器"""
    
    story_id: str
    chapter_id: str
    user_id: str
    
    @validator("story_id")
    def validate_story_id(cls, v):
        if not v or len(v) == 0:
            raise ValueError("story_id cannot be empty")
        return v
    
    @validator("chapter_id")
    def validate_chapter_id(cls, v):
        if not v or len(v) == 0:
            raise ValueError("chapter_id cannot be empty")
        return v


def validate_state(state: NovelState) -> bool:
    """验证状态"""
    try:
        NovelStateValidator(**state)
        return True
    except Exception as e:
        logger.error(f"State validation failed: {e}")
        return False
```

---

## 状态快照

```python
import json
from datetime import datetime

def create_state_snapshot(state: NovelState) -> Dict[str, Any]:
    """创建状态快照（用于 Checkpoint）"""
    return {
        "state": state.copy(),
        "timestamp": datetime.now().isoformat(),
        "version": "1.0"
    }


def restore_state_snapshot(snapshot: Dict[str, Any]) -> NovelState:
    """从快照恢复状态"""
    return snapshot["state"]
```

---

## 状态压缩

```python
def compress_state_for_checkpoint(state: NovelState) -> NovelState:
    """
    压缩状态用于 Checkpoint
    
    移除不必要的数据，减少存储空间
    """
    compressed = state.copy()
    
    # 只保留摘要，不保存完整章节内容
    if "novel_context" in compressed:
        context = compressed["novel_context"]
        if "recent_chapters" in context:
            # 只保存章节 ID，不保存完整内容
            context["recent_chapters"] = [
                {"id": ch["id"], "title": ch["title"]}
                for ch in context["recent_chapters"]
            ]
    
    return compressed
```

---

## 多工作流状态

### Workflow 1: 章节生成

```python
class ChapterGenerationState(NovelState):
    """章节生成工作流状态"""
    pass  # 使用基础 NovelState
```

### Workflow 2: 小说规划

```python
class NovelPlanningState(TypedDict, total=False):
    """小说规划工作流状态"""
    
    story_id: str
    genre: str  # 题材
    target_words: int  # 目标字数
    
    world_setting: Dict[str, Any]  # 世界设定
    character_designs: List[Dict[str, Any]]  # 人物设计
    plot_outline: Dict[str, Any]  # 剧情大纲
    
    execution_history: List[str]
    checkpoint_id: Optional[str]
```

---

## 状态迁移

```python
def migrate_state_v1_to_v2(old_state: Dict[str, Any]) -> NovelState:
    """
    状态版本迁移
    
    当 State Schema 升级时，迁移旧版本状态
    """
    new_state = NovelState(
        story_id=old_state["story_id"],
        chapter_id=old_state["chapter_id"],
        user_id=old_state.get("user_id", "unknown"),  # 新增字段
        novel_context=old_state.get("context", {}),  # 字段重命名
        chapter_outline=old_state.get("outline", {}),
        generated_draft=old_state.get("draft", ""),
        consistency_report=old_state.get("consistency", {}),
        review_report=old_state.get("review", {}),
        execution_history=old_state.get("history", []),
        current_node=None,  # 新增字段
        checkpoint_id=old_state.get("checkpoint_id"),
        checkpoint_timestamp=None,  # 新增字段
        error=None,
        retry_count=0,  # 新增字段
        metadata={}  # 新增字段
    )
    
    return new_state
```

---

## 状态调试

```python
def debug_state(state: NovelState, message: str = ""):
    """调试状态"""
    logger.debug(f"=== State Debug: {message} ===")
    logger.debug(f"Story ID: {state.get('story_id')}")
    logger.debug(f"Chapter ID: {state.get('chapter_id')}")
    logger.debug(f"Current Node: {state.get('current_node')}")
    logger.debug(f"Execution History: {state.get('execution_history')}")
    logger.debug(f"Error: {state.get('error')}")
    logger.debug(f"Retry Count: {state.get('retry_count')}")
    
    # 检查关键字段
    if not state.get("generated_draft"):
        logger.warning("Generated draft is empty")
    
    if state.get("consistency_report", {}).get("total_issues", 0) > 0:
        logger.warning(f"Consistency issues found: {state['consistency_report']['total_issues']}")
```

---

## 最佳实践

1. **使用 TypedDict** - 提供类型提示，便于 IDE 支持
2. **total=False** - 允许部分字段可选
3. **不可变更新** - 节点返回新状态，不修改输入
4. **文档注释** - 为每个字段添加说明
5. **状态验证** - 关键节点验证状态完整性
6. **状态压缩** - Checkpoint 前压缩状态
7. **版本管理** - 支持状态 Schema 升级迁移
