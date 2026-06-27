"""Draft quality review service for Java-supplied writing context."""

import json
from typing import Any

from pydantic import ValidationError

from src.models.llm_client import llm_stream_with_fallback
from src.models.provider import agent_model_chain, agent_temperature
from src.schemas.review import DraftQualityReviewReport

REVIEW_SYSTEM_PROMPT = """你是 DreamWeaver 的正文质量评审 Agent，只负责评审已经生成的章节正文。
你必须基于 Java 传入的 confirmed blueprint、confirmedOutline.finalOutline、recentChapters、extraPrompt 和 draft 做判断。

评审重点：
1. 正文是否严格遵守 confirmedOutline，尤其是 sceneOutline 顺序、chapterGoal、endingHook。
2. 正文是否违背 blueprint、worldSeed、lockedFacts、protagonist、mainThread、coreConflict。
3. 正文完整度、节奏、可读性、人物表现、冲突推进是否符合目标章节。
4. 是否存在需要 P0 自动修复的阻塞问题。

严重级别：
- P0：阻塞级问题。包括推翻 lockedFacts、违背 confirmedOutline 关键剧情、主角/世界观/时间线重大矛盾、正文缺失关键场景或结尾钩子。P0 必须 blocking=true 且 autoRepairRequired=true。
- P1：重要但非阻塞问题。包括节奏明显失衡、人物动机薄弱、关键过渡缺失、局部连续性问题。
- P2：润色建议。包括语言重复、句式单调、局部描写可增强。

category 只能使用：plot、character、world、timeline、foreshadow、style、pacing、continuity。
只输出一个 JSON 对象，不要输出 Markdown、代码块、解释或额外文本。
JSON 必须符合：
{
  "overallScore": 0-100,
  "summary": "一句到三句话总结",
  "issues": [
    {
      "severity": "P0|P1|P2",
      "category": "plot|character|world|timeline|foreshadow|style|pacing|continuity",
      "message": "问题说明",
      "evidence": "引用或概括正文/中纲/蓝图中的证据",
      "suggestion": "可执行修复建议",
      "sceneIndex": 0
    }
  ],
  "blocking": false,
  "autoRepairRequired": false,
  "revisionHints": ["后续修改提示"],
  "strengths": ["正文优点"]
}
"""

REVIEW_HUMAN_PROMPT = """请评审以下已生成章节正文。

【小说】
{story}

【目标章节】
{chapter}

【已确认小说蓝图】
{blueprint}

【已确认章节中纲 confirmedOutline】
{confirmed_outline}

【必须遵守的 finalOutline】
{final_outline}

【最近章节】
{recent_chapters}

【作者额外提示】
{extra_prompt}

【目标字数】
{target_words}

【待评审正文 draft】
{draft}

请只返回 DraftQualityReviewReport JSON。"""


class ReviewGenerationError(RuntimeError):
    """Raised when the reviewer cannot produce a valid review report."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def build_review_quality_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    """Build reviewer messages from generated draft and confirmed writing context."""
    payload = validate_review_quality_request(request)
    confirmed_outline = payload["confirmedOutline"]
    return [
        {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": REVIEW_HUMAN_PROMPT.format(
                story=_json(payload.get("story")),
                chapter=_json(payload.get("chapter")),
                blueprint=_json(payload.get("blueprint")),
                confirmed_outline=_json(confirmed_outline),
                final_outline=_json(confirmed_outline.get("finalOutline")),
                recent_chapters=_json(payload.get("recentChapters")),
                extra_prompt=payload.get("extraPrompt") or "无",
                target_words=payload.get("targetWords") or "未指定",
                draft=payload["draft"],
            ),
        },
    ]


async def review_quality(request: dict[str, Any]) -> DraftQualityReviewReport:
    """Review a generated draft and return a validated DraftQualityReviewReport."""
    messages = build_review_quality_messages(request)
    raw_response = ""
    async for token in llm_stream_with_fallback(
        messages,
        models=agent_model_chain("review"),
        max_tokens=4096,
        temperature=agent_temperature("review"),
    ):
        raw_response += token
    return parse_review_quality_response(raw_response)


def parse_review_quality_response(raw_response: str) -> DraftQualityReviewReport:
    """Parse and validate the reviewer's JSON-only response."""
    content = _strip_json_fence(raw_response)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ReviewGenerationError(
            "INVALID_REVIEW_JSON",
            f"Reviewer returned invalid JSON: {exc.msg}",
        ) from exc

    try:
        return DraftQualityReviewReport.model_validate(data)
    except ValidationError as exc:
        raise ReviewGenerationError(
            "INVALID_REVIEW_SCHEMA",
            f"Reviewer response failed review schema validation: {exc}",
        ) from exc


def validate_review_quality_request(request: dict[str, Any]) -> dict[str, Any]:
    """Validate required context for quality review."""
    if not isinstance(request, dict):
        raise ReviewGenerationError("INVALID_REVIEW_REQUEST", "review request must be a JSON object")
    if not str(request.get("generationId") or "").strip():
        raise ReviewGenerationError("GENERATION_ID_REQUIRED", "generationId is required")
    if not _non_empty_object(request.get("story")):
        raise ReviewGenerationError("STORY_REQUIRED", "story is required")
    if not _non_empty_object(request.get("chapter")):
        raise ReviewGenerationError("CHAPTER_REQUIRED", "chapter is required")
    if not _non_empty_object(request.get("blueprint")):
        raise ReviewGenerationError("CONFIRMED_BLUEPRINT_REQUIRED", "blueprint is required")
    if not _non_empty_object(request.get("confirmedOutline")):
        raise ReviewGenerationError("CONFIRMED_OUTLINE_REQUIRED", "confirmedOutline is required")
    confirmed_outline = request["confirmedOutline"]
    if not _non_empty_object(confirmed_outline.get("finalOutline")):
        raise ReviewGenerationError(
            "CONFIRMED_FINAL_OUTLINE_REQUIRED",
            "confirmedOutline.finalOutline is required",
        )
    if not str(request.get("draft") or "").strip():
        raise ReviewGenerationError("DRAFT_REQUIRED", "draft is required")
    recent_chapters = request.get("recentChapters", [])
    if recent_chapters is not None and not isinstance(recent_chapters, list):
        raise ReviewGenerationError("INVALID_RECENT_CHAPTERS", "recentChapters must be a list")
    return request


def _strip_json_fence(raw_response: str) -> str:
    content = (raw_response or "").strip()
    if content.startswith("```json"):
        return content.split("```json", 1)[1].split("```", 1)[0].strip()
    if content.startswith("```"):
        return content.split("```", 1)[1].split("```", 1)[0].strip()
    return content


def _json(value: Any) -> str:
    return json.dumps(value or {}, ensure_ascii=False, indent=2, sort_keys=True)


def _non_empty_object(value: Any) -> bool:
    return isinstance(value, dict) and bool(value)
