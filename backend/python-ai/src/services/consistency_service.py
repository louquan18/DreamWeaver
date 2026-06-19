"""P4 consistency checking service for generated drafts."""

import json
from typing import Any

from pydantic import ValidationError

from src.models.llm_client import llm_invoke
from src.models.provider import agent_model_chain, agent_temperature
from src.schemas.consistency import DraftConsistencyReport
from src.services.consistency_rules import default_consistency_rules

CONSISTENCY_SYSTEM_PROMPT = """You are DreamWeaver's check_consistency Agent.
Your only task is to inspect a generated novel chapter draft against the confirmed writing context.

Use every provided consistency rule. Check exactly these domains:
- world
- character
- timeline
- foreshadow

Return strict JSON only. Do not include markdown, commentary, or repair prose outside JSON.
The JSON must match this shape:
{
  "summary": "short consistency summary",
  "issues": [
    {
      "severity": "P0 | P1 | P2",
      "domain": "world | character | timeline | foreshadow",
      "ruleId": "rule id from the supplied rules",
      "message": "clear issue statement",
      "evidence": "quote or concrete draft evidence",
      "suggestion": "specific repair suggestion",
      "location": {
        "chapterId": "optional chapter id",
        "sceneIndex": 0,
        "paragraphIndex": 0,
        "startOffset": 0,
        "endOffset": 0,
        "quote": "optional quote"
      },
      "sceneIndex": 0
    }
  ],
  "checkedRuleIds": ["all rule ids you checked"],
  "passedRuleIds": ["rule ids with no issue"],
  "blocking": false,
  "autoRepairRequired": false
}

Severity policy:
- P0: blocking contradiction. These issues must require automatic repair.
- P1: important continuity drift. Not blocking by default.
- P2: minor continuity risk. Not blocking by default.

If there are no issues, return an empty issues array with checkedRuleIds populated.
"""

CONSISTENCY_HUMAN_PROMPT = """Check the draft with the supplied rules and context.

[generationId]
{generation_id}

[consistencyRules]
{rules}

[story]
{story}

[chapter]
{chapter}

[confirmedBlueprint]
{blueprint}

[confirmedOutline]
{confirmed_outline}

[recentChapters]
{recent_chapters}

[activeForeshadows]
{active_foreshadows}

[timeline]
{timeline}

[characters]
{characters}

[worldState]
{world_state}

[draft]
{draft}
"""


class ConsistencyCheckError(RuntimeError):
    """Raised when check_consistency cannot produce a valid report."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def build_consistency_check_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    """Build messages for the P4 check_consistency task."""
    normalized = validate_consistency_check_request(request)
    rules = [rule.model_dump(by_alias=True) for rule in default_consistency_rules()]
    return [
        {"role": "system", "content": CONSISTENCY_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": CONSISTENCY_HUMAN_PROMPT.format(
                generation_id=normalized["generationId"],
                rules=_json(rules),
                story=_json(normalized["story"]),
                chapter=_json(normalized["chapter"]),
                blueprint=_json(normalized["blueprint"]),
                confirmed_outline=_json(normalized["confirmedOutline"]),
                recent_chapters=_json(normalized.get("recentChapters", [])),
                active_foreshadows=_json(normalized.get("activeForeshadows", [])),
                timeline=_json(normalized.get("timeline", [])),
                characters=_json(normalized.get("characters", {})),
                world_state=_json(normalized.get("worldState", {})),
                draft=normalized["draft"],
            ),
        },
    ]


async def check_consistency(request: dict[str, Any]) -> DraftConsistencyReport:
    """Run check_consistency and return a validated DraftConsistencyReport."""
    messages = build_consistency_check_messages(request)
    response_text = await _invoke_consistency_model(messages)
    return parse_consistency_report(response_text)


def validate_consistency_check_request(request: dict[str, Any]) -> dict[str, Any]:
    """Validate the Java-owned context needed by check_consistency."""
    if not isinstance(request, dict):
        raise ConsistencyCheckError(
            "INVALID_CONSISTENCY_REQUEST",
            "consistency request must be a JSON object",
        )

    normalized = dict(request)
    required_objects = ("story", "chapter", "blueprint", "confirmedOutline")
    if not str(normalized.get("generationId") or "").strip():
        raise ConsistencyCheckError("GENERATION_ID_REQUIRED", "generationId is required")
    for key in required_objects:
        if not isinstance(normalized.get(key), dict) or not normalized[key]:
            raise ConsistencyCheckError(
                f"{_constant_case(key)}_REQUIRED",
                f"{key} is required for consistency checking",
            )
    if not isinstance(normalized["confirmedOutline"].get("finalOutline"), dict) or not normalized[
        "confirmedOutline"
    ]["finalOutline"]:
        raise ConsistencyCheckError(
            "CONFIRMED_FINAL_OUTLINE_REQUIRED",
            "confirmedOutline.finalOutline is required for consistency checking",
        )
    if not str(normalized.get("draft") or "").strip():
        raise ConsistencyCheckError("DRAFT_REQUIRED", "draft is required for consistency checking")

    normalized["generationId"] = str(normalized["generationId"]).strip()
    normalized["draft"] = str(normalized["draft"]).strip()
    normalized.setdefault("recentChapters", [])
    normalized.setdefault("activeForeshadows", [])
    normalized.setdefault("timeline", [])
    normalized.setdefault("characters", {})
    normalized.setdefault("worldState", {})
    return normalized


def parse_consistency_report(response_text: str) -> DraftConsistencyReport:
    """Parse and validate the LLM JSON response."""
    try:
        payload = json.loads(_strip_json_fence(response_text))
    except json.JSONDecodeError as exc:
        raise ConsistencyCheckError("INVALID_CONSISTENCY_JSON", str(exc)) from exc

    try:
        return DraftConsistencyReport.model_validate(payload)
    except ValidationError as exc:
        raise ConsistencyCheckError("INVALID_CONSISTENCY_REPORT", str(exc)) from exc


async def _invoke_consistency_model(messages: list[dict[str, str]]) -> str:
    models = agent_model_chain("consistency")
    temperature = agent_temperature("consistency")
    last_exc: Exception | None = None

    for model in models:
        try:
            return await llm_invoke(
                messages,
                model=model,
                max_tokens=4096,
                temperature=temperature,
            )
        except Exception as exc:  # noqa: BLE001 - fallback across configured consistency models
            last_exc = exc
            continue

    raise ConsistencyCheckError(
        "CONSISTENCY_MODEL_ERROR",
        str(last_exc) if last_exc is not None else "no consistency model configured",
    )


def _strip_json_fence(text: str) -> str:
    content = (text or "").strip()
    if content.startswith("```json"):
        return content.removeprefix("```json").removesuffix("```").strip()
    if content.startswith("```"):
        return content.removeprefix("```").removesuffix("```").strip()
    return content


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, indent=2, sort_keys=True)


def _constant_case(value: str) -> str:
    result: list[str] = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            result.append("_")
        result.append(char.upper())
    return "".join(result)
