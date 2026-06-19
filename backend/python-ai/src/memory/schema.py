"""结构化记忆 Schema - 四层记忆的数据模型"""

from typing import Any, ClassVar

from pydantic import BaseModel, Field, field_validator, model_validator


# ========== Timeline ==========


class TimelineEvent(BaseModel):
    """时间线事件"""

    chapter: int = Field(..., description="章节号")
    event: str = Field(..., description="事件描述")
    characters: list[str] = Field(default_factory=list, description="涉及人物")
    importance: str = Field("medium", description="重要性: high/medium/low")
    is_permanent: bool = Field(False, description="永久保留标记（主角觉醒、世界观确立等关键节点）")


# ========== Character Graph ==========


class Relationship(BaseModel):
    """人物关系"""

    type: str = Field(..., description="关系类型（好友/敌人/师徒/恋人等）")
    closeness: int = Field(0, description="亲密度 -100~100")


class CultivationState(BaseModel):
    """人物修炼状态 - 结构化字段，防止 LLM 提取的字段名漂移"""

    cultivation_level: str = Field("", description="修炼境界，如：炼气三层、筑基初期")
    spirit_root: str = Field("", description="灵根属性")
    location: str = Field("", description="当前所在位置")
    health_status: str = Field("正常", description="健康状态")
    special_abilities: list[str] = Field(default_factory=list, description="特殊能力")
    equipment: list[str] = Field(default_factory=list, description="装备")


class CharacterState(BaseModel):
    """人物状态"""

    name: str
    current_state: CultivationState = Field(default_factory=CultivationState)
    relationships: dict[str, Relationship] = Field(default_factory=dict)
    personality_traits: list[str] = Field(default_factory=list)
    last_appeared: int = Field(0, description="最后出现的章节号")


# ========== Foreshadow Memory ==========


class Foreshadow(BaseModel):
    """伏笔记录（支持生命周期管理）"""

    LIFECYCLE_STATUSES: ClassVar[set[str]] = {
        "planned",
        "planted",
        "reinforced",
        "triggered",
        "revealed",
        "resolved",
        "abandoned",
    }
    OPEN_STATUSES: ClassVar[set[str]] = {
        "planned",
        "planted",
        "reinforced",
        "triggered",
        "revealed",
    }
    TERMINAL_STATUSES: ClassVar[set[str]] = {"resolved", "abandoned"}
    ATTENTION_STATUSES: ClassVar[set[str]] = {"normal", "due_soon", "overdue"}

    id: str = Field(..., description="伏笔 ID")
    chapter_planted: int = Field(..., description="埋设章节")
    content: str = Field(..., description="伏笔内容")
    trigger_condition: str = Field("", description="触发条件")
    status: str = Field(
        "planted",
        description="生命周期状态: planned/planted/reinforced/triggered/revealed/resolved/abandoned",
    )
    importance: str = Field("medium", description="重要性: high/medium/low")
    title: str = Field("", description="短标题")
    planned_payoff_hint: str = Field("", description="计划回收方向")
    related_characters: list[str] = Field(default_factory=list, description="相关人物")
    related_items: list[str] = Field(default_factory=list, description="相关道具")
    related_locations: list[str] = Field(default_factory=list, description="相关地点")
    related_world_rules: list[str] = Field(default_factory=list, description="相关世界规则")
    attention_status: str = Field(
        "normal",
        description="关注状态: normal/due_soon/overdue",
    )
    needs_attention: bool = Field(False, description="是否需要优先处理")
    state_history: list[dict[str, Any]] = Field(default_factory=list, description="状态变更历史")
    age: int = Field(0, description="已存在章节数（每章+1）")
    max_age: int = Field(20, description="最大存活章节数，超期后设置 attention_status")
    last_checked_chapter: int = Field(0, description="上次被检查触发条件的章节")

    @model_validator(mode="before")
    @classmethod
    def normalize_legacy_status(cls, data: Any) -> Any:
        """Map legacy active/overdue statuses into the P1 lifecycle model."""
        if not isinstance(data, dict):
            return data

        normalized = dict(data)
        status = normalized.get("status")
        if status == "active":
            normalized["status"] = "planted"
        elif status == "overdue":
            normalized["status"] = "planted"
            normalized["attention_status"] = "overdue"
            normalized["needs_attention"] = True

        if normalized.get("attention_status") == "overdue":
            normalized["needs_attention"] = True

        return normalized

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if value not in cls.LIFECYCLE_STATUSES:
            allowed = ", ".join(sorted(cls.LIFECYCLE_STATUSES))
            raise ValueError(f"status must be one of: {allowed}")
        return value

    @field_validator("attention_status")
    @classmethod
    def validate_attention_status(cls, value: str) -> str:
        if value not in cls.ATTENTION_STATUSES:
            allowed = ", ".join(sorted(cls.ATTENTION_STATUSES))
            raise ValueError(f"attention_status must be one of: {allowed}")
        return value


# ========== World State ==========


class WorldState(BaseModel):
    """世界状态"""

    forces: dict[str, dict[str, str]] = Field(default_factory=dict)
    locations: dict[str, dict[str, str]] = Field(default_factory=dict)
    rules: dict[str, str] = Field(default_factory=dict)


# ========== Unified Memory ==========


class NovelMemory(BaseModel):
    """小说完整记忆"""

    timeline: list[TimelineEvent] = Field(default_factory=list)
    characters: dict[str, CharacterState] = Field(default_factory=dict)
    foreshadows: list[Foreshadow] = Field(default_factory=list)
    world_state: WorldState = Field(default_factory=WorldState)


# ========== Compression Result ==========


class CompressionResult(BaseModel):
    """章节压缩结果"""

    summary: str = Field("", description="章节摘要")
    events: list[TimelineEvent] = Field(default_factory=list)
    character_changes: dict[str, dict[str, Any]] = Field(default_factory=dict)
    original_length: int = Field(0)
    compressed_length: int = Field(0)
    compression_rate: float = Field(0.0)
    original_chapter_ref: str = Field("", description="原文存储引用（DB 主键或文件路径）")

    def calculate_rate(self) -> float:
        if self.original_length == 0:
            return 0.0
        self.compression_rate = 1 - (self.compressed_length / self.original_length)
        return self.compression_rate
