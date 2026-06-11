"""一致性检测规则库

定义人物/世界观/情节三个维度的具体检测规则。
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class Severity(str, Enum):
    HIGH = "high"      # 必须修复：严重矛盾
    MEDIUM = "medium"  # 建议修复：不一致
    LOW = "low"        # 可忽略：轻微偏差


class IssueCategory(str, Enum):
    # 人物维度
    CHARACTER_PERSONALITY = "character_personality"    # 性格漂移
    CHARACTER_ABILITY = "character_ability"            # 能力异常
    CHARACTER_RELATIONSHIP = "character_relationship"  # 关系矛盾
    CHARACTER_CALLED = "character_called"              # 称谓不一致
    CHARACTER_DEATH = "character_death"                # 死活矛盾

    # 世界观维度
    WORLD_RULE = "world_rule"              # 规则违反
    WORLD_SETTING = "world_setting"        # 设定矛盾
    WORLD_GEOGRAPHY = "world_geography"    # 地理错误
    WORLD_TIMELINE = "world_timeline"      # 时间线矛盾

    # 情节维度
    PLOT_FORESHADOW = "plot_foreshadow"    # 伏笔遗失
    PLOT_CAUSALITY = "plot_causality"      # 因果缺失
    PLOT_JUMP = "plot_jump"                # 剧情跳跃
    PLOT_CONTRADICTION = "plot_contradiction"  # 情节自相矛盾


class ConsistencyIssue(BaseModel):
    """单个一致性问题"""

    category: IssueCategory
    severity: Severity
    description: str = Field(..., description="问题描述")
    location: str = Field("", description="问题出现的大致位置")
    suggestion: str = Field("", description="修复建议")


class ConsistencyRule(BaseModel):
    """一致性检测规则"""

    id: str
    name: str
    category: IssueCategory
    severity: Severity
    check_prompt: str  # 用于 LLM 检测的 prompt 片段


# ========== 规则库 ==========

CHARACTER_RULES = [
    ConsistencyRule(
        id="C01",
        name="性格一致性",
        category=IssueCategory.CHARACTER_PERSONALITY,
        severity=Severity.HIGH,
        check_prompt="""
检查人物性格是否与设定一致：
- 人物在对话和行为中表现出的性格特征是否与其 personality_traits 匹配
- 是否出现突然的性格转变（无剧情铺垫）
- 人物的决策逻辑是否符合其性格
""",
    ),
    ConsistencyRule(
        id="C02",
        name="能力边界",
        category=IssueCategory.CHARACTER_ABILITY,
        severity=Severity.HIGH,
        check_prompt="""
检查人物能力是否超出已知范围：
- 使用的技能/力量是否在之前章节中出现过或有铺垫
- 等级/实力是否与 current_state 中的记录匹配
- 是否出现"突然学会"某技能而无解释
""",
    ),
    ConsistencyRule(
        id="C03",
        name="关系一致性",
        category=IssueCategory.CHARACTER_RELATIONSHIP,
        severity=Severity.MEDIUM,
        check_prompt="""
检查人物关系是否正确：
- 人物之间的称呼和互动方式是否与关系设定匹配
- 敌对关系是否出现了无原因的友好互动
- 亲密关系是否出现了无原因的冷漠
""",
    ),
    ConsistencyRule(
        id="C04",
        name="称谓一致性",
        category=IssueCategory.CHARACTER_CALLED,
        severity=Severity.LOW,
        check_prompt="""
检查称谓是否一致：
- 同一人物在不同段落中的称呼是否一致
- 人物名字是否有拼写变化
- 敬称/昵称的使用是否合理
""",
    ),
    ConsistencyRule(
        id="C05",
        name="生死一致性",
        category=IssueCategory.CHARACTER_DEATH,
        severity=Severity.HIGH,
        check_prompt="""
检查人物生死状态：
- 已确认死亡的人物是否再次出现（无复活设定时）
- 重伤人物是否突然恢复行动能力
- 人物的伤亡状态是否与之前章节一致
""",
    ),
]

WORLD_RULES = [
    ConsistencyRule(
        id="W01",
        name="力量体系",
        category=IssueCategory.WORLD_RULE,
        severity=Severity.HIGH,
        check_prompt="""
检查力量体系是否自洽：
- 修炼等级/技能等级是否符合已建立的体系
- 等级压制关系是否被违反
- 力量使用是否有合理的代价/限制
""",
    ),
    ConsistencyRule(
        id="W02",
        name="世界设定",
        category=IssueCategory.WORLD_SETTING,
        severity=Severity.MEDIUM,
        check_prompt="""
检查世界设定是否矛盾：
- 引入的新元素是否与已有设定冲突
- 社会制度/文化习俗是否前后一致
- 科技/魔法水平是否合理
""",
    ),
    ConsistencyRule(
        id="W03",
        name="地理一致性",
        category=IssueCategory.WORLD_GEOGRAPHY,
        severity=Severity.LOW,
        check_prompt="""
检查地理描述是否一致：
- 地名、距离、方位是否与之前描述匹配
- 人物移动速度是否合理
- 地点特征是否前后一致
""",
    ),
]

PLOT_RULES = [
    ConsistencyRule(
        id="P01",
        name="伏笔追踪",
        category=IssueCategory.PLOT_FORESHADOW,
        severity=Severity.MEDIUM,
        check_prompt="""
检查伏笔是否被妥善处理：
- 已埋设的活跃伏笔是否在合适的时机被推进或回收
- 是否有伏笔被遗忘（超过 10 章未提及）
- 新的伏笔是否与已有伏笔冲突
""",
    ),
    ConsistencyRule(
        id="P02",
        name="因果链完整性",
        category=IssueCategory.PLOT_CAUSALITY,
        severity=Severity.HIGH,
        check_prompt="""
检查因果关系是否完整：
- 重大事件是否有合理的前因
- 人物决策是否有充分的动机
- 结果是否与原因的严重程度匹配
""",
    ),
    ConsistencyRule(
        id="P03",
        name="剧情连贯性",
        category=IssueCategory.PLOT_JUMP,
        severity=Severity.MEDIUM,
        check_prompt="""
检查剧情是否有跳跃：
- 场景切换是否有过渡
- 时间跳跃是否有交代
- 人物位置变化是否合理
""",
    ),
    ConsistencyRule(
        id="P04",
        name="情节自洽",
        category=IssueCategory.PLOT_CONTRADICTION,
        severity=Severity.HIGH,
        check_prompt="""
检查情节是否自相矛盾：
- 本章内容是否与之前的事实描述冲突
- 是否出现了逻辑悖论
- 事件的先后顺序是否合理
""",
    ),
]

ALL_RULES = CHARACTER_RULES + WORLD_RULES + PLOT_RULES


def get_rules_by_category(category: IssueCategory) -> list[ConsistencyRule]:
    """按类别获取规则"""
    return [r for r in ALL_RULES if r.category == category]


def get_rules_by_severity(severity: Severity) -> list[ConsistencyRule]:
    """按严重性获取规则"""
    return [r for r in ALL_RULES if r.severity == severity]


def build_rule_check_prompt() -> str:
    """构建完整的规则检查 prompt"""
    sections = []

    sections.append("## 人物一致性规则")
    for r in CHARACTER_RULES:
        sections.append(f"### [{r.id}] {r.name} ({r.severity.value})")
        sections.append(r.check_prompt.strip())

    sections.append("\n## 世界观一致性规则")
    for r in WORLD_RULES:
        sections.append(f"### [{r.id}] {r.name} ({r.severity.value})")
        sections.append(r.check_prompt.strip())

    sections.append("\n## 情节一致性规则")
    for r in PLOT_RULES:
        sections.append(f"### [{r.id}] {r.name} ({r.severity.value})")
        sections.append(r.check_prompt.strip())

    return "\n".join(sections)
