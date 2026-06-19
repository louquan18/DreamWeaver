"""Lightweight novel blueprint generation service."""

import json
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from loguru import logger
from pydantic import ValidationError

from src.models.provider import get_agent_llm
from src.schemas.blueprint import (
    BlueprintValidationIssue,
    LightBlueprintGenerateRequest,
    NovelBlueprintDraft,
)
from src.services.blueprint_validation import BlueprintValidationError, validate_blueprint

BLUEPRINT_SYSTEM_PROMPT = """你是 DreamWeaver 的小说蓝图生成 Agent。
你的任务是把作者的一句话小说设想，扩展成轻量、可编辑、适合后续章节规划的 NovelBlueprint。

只输出一个 JSON object，不要输出 Markdown、解释或额外文本。JSON 必须包含这些字段：
{
  "premise": "一句话故事核心",
  "genre": "题材",
  "tone": "风格与节奏",
  "protagonist": {
    "name": "主角名",
    "identity": "初始身份",
    "initialGoal": "初始目标",
    "motivation": "核心动机",
    "traits": ["性格标签"]
  },
  "mainThread": {
    "goal": "长期主线目标",
    "stages": [{"order": 1, "name": "阶段名", "goal": "阶段目标"}],
    "antagonistOrObstacle": "主要阻力"
  },
  "coreConflict": {
    "external": "外部冲突",
    "internal": "内部冲突",
    "stakes": "失败代价"
  },
  "worldSeed": {
    "rules": [{"id": "world-rule-001", "description": "关键世界规则", "locked": true}],
    "factions": [],
    "locations": [],
    "powerLimits": []
  },
  "writingPreferences": {
    "pace": "节奏",
    "style": "文风",
    "tone": "基调",
    "avoid": []
  },
  "lockedFacts": [
    {"id": "fact-001", "text": "后续不能违背的设定", "category": "world", "source": "agent"}
  ]
}

要求：
- 信息不足时，可以做合理文学创作补全，但不能声称来自作者未提供的真实资料。
- lockedFacts 只放会影响后续一致性的硬约束。
- protagonist、mainThread、coreConflict、worldSeed 必须是 JSON object。
- lockedFacts 必须是 JSON array，每项必须有 text。
"""

BLUEPRINT_HUMAN_PROMPT = """作者设想：
{source_prompt}

可选提示：
{hints}

请生成轻量小说蓝图。"""

LLMInvoker = Callable[[list[Any]], Awaitable[str]]


class BlueprintGenerationError(RuntimeError):
    """Raised when the LLM response cannot be converted to a valid blueprint."""


async def generate_light_blueprint(
    story_id: str,
    request: LightBlueprintGenerateRequest,
    llm: Any | LLMInvoker | None = None,
) -> NovelBlueprintDraft:
    """Generate a structured lightweight NovelBlueprint from an author idea."""
    logger.info(f"[Blueprint Agent] Generating light blueprint for story={story_id}")
    hints = _build_hints(request)
    messages = [
        SystemMessage(content=BLUEPRINT_SYSTEM_PROMPT),
        HumanMessage(
            content=BLUEPRINT_HUMAN_PROMPT.format(
                source_prompt=request.source_prompt,
                hints=json.dumps(hints, ensure_ascii=False, indent=2),
            )
        ),
    ]

    content = await _invoke_llm(messages, llm)
    payload = _parse_json_object(content)
    normalized = _normalize_payload(story_id, request, payload)

    try:
        blueprint = NovelBlueprintDraft.model_validate(normalized)
    except ValidationError as exc:
        raise BlueprintValidationError(_issues_from_schema_error(exc)) from exc

    validation = validate_blueprint(blueprint)
    if validation.has_blocking_errors:
        raise BlueprintValidationError(validation.errors)
    blueprint.validation_issues = validation.warnings

    logger.info(
        "[Blueprint Agent] Blueprint generated: "
        f"story={story_id}, premise={blueprint.premise[:40]}"
    )
    return blueprint


def _build_hints(request: LightBlueprintGenerateRequest) -> dict[str, Any]:
    hints: dict[str, Any] = dict(request.preferences)
    if request.genre:
        hints["genre"] = request.genre
    if request.tone:
        hints["tone"] = request.tone
    if request.target_words:
        hints["targetWords"] = request.target_words
    return hints


async def _invoke_llm(messages: list[Any], llm: Any | LLMInvoker | None) -> str:
    runner = llm or get_agent_llm("blueprint")

    try:
        if callable(runner) and not hasattr(runner, "ainvoke"):
            return await runner(messages)

        response = await runner.ainvoke(messages)
        content = getattr(response, "content", response)
        if not isinstance(content, str):
            raise TypeError("LLM response content must be a string")
        return content
    except Exception as exc:
        raise BlueprintGenerationError(f"LLM invocation failed: {exc}") from exc


def _parse_json_object(content: str) -> dict[str, Any]:
    text = content.strip()
    if "```json" in text:
        text = text.split("```json", 1)[1].split("```", 1)[0].strip()
    elif "```" in text:
        text = text.split("```", 1)[1].split("```", 1)[0].strip()
    else:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and start < end:
            text = text[start : end + 1]

    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise BlueprintGenerationError(f"LLM did not return valid JSON: {exc}") from exc

    if not isinstance(payload, dict):
        raise BlueprintGenerationError("LLM JSON response must be an object")
    return payload


def _normalize_payload(
    story_id: str,
    request: LightBlueprintGenerateRequest,
    payload: dict[str, Any],
) -> dict[str, Any]:
    writing_preferences = _object_value(payload, "writing_preferences", "writingPreferences")
    if request.target_words and "targetWords" not in writing_preferences:
        writing_preferences["targetWords"] = request.target_words
    if request.tone and "tone" not in writing_preferences:
        writing_preferences["tone"] = request.tone

    return {
        "story_id": story_id,
        "source_prompt": request.source_prompt,
        "premise": str(payload.get("premise", "")).strip(),
        "genre": request.genre or payload.get("genre"),
        "tone": request.tone or payload.get("tone"),
        "protagonist": _object_value(payload, "protagonist"),
        "main_thread": _object_value(payload, "main_thread", "mainThread"),
        "core_conflict": _object_value(payload, "core_conflict", "coreConflict"),
        "world_seed": _object_value(payload, "world_seed", "worldSeed"),
        "writing_preferences": writing_preferences,
        "locked_facts": _normalize_locked_facts(
            payload.get("locked_facts", payload.get("lockedFacts", []))
        ),
        "status": "generated",
    }


def _object_value(payload: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = payload.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _normalize_locked_facts(value: Any) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise BlueprintValidationError(
            [
                BlueprintValidationIssue(
                    code="LOCKED_FACTS_NOT_ARRAY",
                    path="lockedFacts",
                    message="lockedFacts must be an array",
                    severity="error",
                    blocking=True,
                )
            ]
        )

    normalized: list[dict[str, Any]] = []
    for idx, item in enumerate(value, start=1):
        if isinstance(item, str):
            text = item.strip()
            if text:
                normalized.append(
                    {
                        "id": f"fact-{idx:03d}",
                        "text": text,
                        "category": "plot",
                        "source": "agent",
                    }
                )
            continue
        if isinstance(item, dict):
            normalized.append(item)
            continue
        raise BlueprintValidationError(
            [
                BlueprintValidationIssue(
                    code="LOCKED_FACT_INVALID_ITEM",
                    path=f"lockedFacts[{idx - 1}]",
                    message="each lockedFacts item must be an object or string",
                    severity="error",
                    blocking=True,
                )
            ]
        )
    return normalized


def _issues_from_schema_error(exc: ValidationError) -> list[BlueprintValidationIssue]:
    issues: list[BlueprintValidationIssue] = []
    for error in exc.errors():
        issues.append(
            BlueprintValidationIssue(
                code="SCHEMA_VALIDATION_ERROR",
                path=_schema_path(error.get("loc", ())),
                message=str(error.get("msg", "invalid blueprint schema")),
                severity="error",
                blocking=True,
            )
        )
    return issues


def _schema_path(loc: Any) -> str:
    aliases = {
        "story_id": "storyId",
        "source_prompt": "sourcePrompt",
        "main_thread": "mainThread",
        "core_conflict": "coreConflict",
        "world_seed": "worldSeed",
        "writing_preferences": "writingPreferences",
        "locked_facts": "lockedFacts",
        "validation_issues": "validationIssues",
    }
    if not isinstance(loc, tuple):
        return str(loc)
    parts: list[str] = []
    for item in loc:
        if isinstance(item, int) and parts:
            parts[-1] = f"{parts[-1]}[{item}]"
        else:
            parts.append(aliases.get(str(item), str(item)))
    return ".".join(parts)
