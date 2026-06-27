"""P0 auto-repair service for generated drafts."""

import hashlib
import json
from typing import Any

from pydantic import ValidationError

from src.models.llm_client import llm_stream_with_fallback
from src.models.provider import agent_model_chain, agent_temperature
from src.schemas.repair import DraftRepairRequest, DraftRepairResult

REPAIR_SYSTEM_PROMPT = """You are DreamWeaver's P0 auto-repair Agent.
Your task is to repair only blocking P0 draft issues identified by the quality reviewer
and consistency checker.

Hard constraints:
- Repair only the supplied P0 issues. Ignore P1/P2 issues for automatic repair.
- Do not rewrite unaffected passages unless a local edit cannot satisfy the P0 issue.
- Do not change the confirmed outline, scene order, chapter goal, or ending hook.
- Do not contradict blueprint.lockedFacts.
- Preserve the author's style, target chapter intent, and recent continuity.
- Return strict JSON only. Do not include markdown, comments, or prose outside JSON.

The JSON must match this shape:
{
  "generationId": "same generation id",
  "repairedDraft": "complete repaired draft",
  "repairSummary": "short explanation of what changed",
  "repairedIssueIds": ["issue ids fully repaired"],
  "remainingIssueIds": ["issue ids still unresolved"],
  "strategy": "local | full_chapter",
  "changed": true
}
"""

REPAIR_HUMAN_PROMPT = """Repair this generated chapter draft.

[generationId]
{generation_id}

[story]
{story}

[chapter]
{chapter}

[confirmedBlueprint]
{blueprint}

[blueprint.lockedFacts]
{locked_facts}

[confirmedOutline]
{confirmed_outline}

[confirmedOutline.finalOutline]
{final_outline}

[recentChapters]
{recent_chapters}

[extraPrompt]
{extra_prompt}

[originalDraft]
{draft}

[P0 review issues to repair]
{review_issues}

[P0 consistency issues to repair]
{consistency_issues}

[maxRepairRounds]
{max_repair_rounds}

Return only DraftRepairResult JSON. repairedIssueIds and remainingIssueIds must use the exact issue ids supplied above.
"""


class RepairGenerationError(RuntimeError):
    """Raised when P0 auto repair cannot produce a valid structured result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def validate_repair_request(request: dict[str, Any]) -> DraftRepairRequest:
    """Validate the P0 auto-repair request."""
    try:
        return DraftRepairRequest.model_validate(request)
    except ValidationError as exc:
        raise RepairGenerationError(
            "INVALID_REPAIR_REQUEST",
            f"Repair request failed schema validation: {exc}",
        ) from exc


def build_repair_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    """Build rewrite-agent messages for P0 auto repair."""
    payload = validate_repair_request(request)
    review_issues, consistency_issues = p0_repair_issues(payload)
    return [
        {"role": "system", "content": REPAIR_SYSTEM_PROMPT},
        {
            "role": "user",
            "content": REPAIR_HUMAN_PROMPT.format(
                generation_id=payload.generation_id,
                story=_json(payload.story),
                chapter=_json(payload.chapter),
                blueprint=_json(payload.blueprint),
                locked_facts=_json(payload.blueprint.get("lockedFacts", [])),
                confirmed_outline=_json(payload.confirmed_outline),
                final_outline=_json(payload.confirmed_outline.get("finalOutline")),
                recent_chapters=_json(payload.recent_chapters),
                extra_prompt=payload.extra_prompt or "None",
                draft=payload.draft,
                review_issues=_json(review_issues),
                consistency_issues=_json(consistency_issues),
                max_repair_rounds=payload.max_repair_rounds,
            ),
        },
    ]


async def auto_repair_p0(request: dict[str, Any]) -> DraftRepairResult:
    """Repair P0 review/consistency issues, or return no-op when no P0 exists."""
    payload = validate_repair_request(request)
    review_issues, consistency_issues = p0_repair_issues(payload)
    if not review_issues and not consistency_issues:
        return DraftRepairResult(
            generationId=payload.generation_id,
            repairedDraft=payload.draft,
            repairSummary="No P0 auto-repair issues found; draft left unchanged.",
            repairedIssueIds=[],
            remainingIssueIds=[],
            strategy="local",
            changed=False,
        )

    raw_response = ""
    async for token in llm_stream_with_fallback(
        build_repair_messages(request),
        models=agent_model_chain("repair"),
        max_tokens=_repair_max_tokens(payload),
        temperature=agent_temperature("repair"),
    ):
        raw_response += token
    result = parse_repair_result(raw_response)
    _assert_result_issue_ids_match(result, review_issues + consistency_issues)
    return result


repair_p0_issues = auto_repair_p0


def parse_repair_result(raw_response: str) -> DraftRepairResult:
    """Parse and validate rewrite-agent JSON output."""
    content = _strip_json_fence(raw_response)
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise RepairGenerationError(
            "INVALID_REPAIR_JSON",
            f"Rewrite agent returned invalid JSON: {exc.msg}",
        ) from exc

    try:
        return DraftRepairResult.model_validate(data)
    except ValidationError as exc:
        raise RepairGenerationError(
            "INVALID_REPAIR_SCHEMA",
            f"Rewrite agent response failed repair schema validation: {exc}",
        ) from exc


def _assert_result_issue_ids_match(
    result: DraftRepairResult,
    p0_issues: list[dict[str, Any]],
) -> None:
    allowed_ids = {str(issue["id"]) for issue in p0_issues}
    returned_ids = set(result.repaired_issue_ids) | set(result.remaining_issue_ids)
    unknown_ids = sorted(returned_ids - allowed_ids)
    if unknown_ids:
        raise RepairGenerationError(
            "INVALID_REPAIR_ISSUE_IDS",
            f"Repair result referenced unknown issue ids: {unknown_ids}",
        )


def p0_repair_issues(payload: DraftRepairRequest) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """Return P0 issues eligible for automatic repair, grouped by report source."""
    review_issues = [
        _issue_payload("review", index, issue.model_dump(by_alias=True))
        for index, issue in enumerate(payload.review_report.issues)
        if issue.severity == "P0" and issue.auto_repair_required
    ]
    consistency_issues = [
        _issue_payload("consistency", index, issue.model_dump(by_alias=True))
        for index, issue in enumerate(payload.consistency_report.issues)
        if issue.severity == "P0" and issue.auto_repair_required
    ]
    return review_issues, consistency_issues


def _issue_payload(source: str, index: int, issue: dict[str, Any]) -> dict[str, Any]:
    fingerprint_source = json.dumps(issue, ensure_ascii=False, sort_keys=True)
    fingerprint = hashlib.sha1(fingerprint_source.encode("utf-8")).hexdigest()[:10]
    return {
        "id": f"{source}:p0:{index}:{fingerprint}",
        "source": source,
        **issue,
    }


def _repair_max_tokens(payload: DraftRepairRequest) -> int:
    draft_chars = len(payload.draft)
    return max(4096, min(12000, int(draft_chars * 1.4) + 2048))


def _strip_json_fence(raw_response: str) -> str:
    content = (raw_response or "").strip()
    if content.startswith("```json"):
        return content.split("```json", 1)[1].split("```", 1)[0].strip()
    if content.startswith("```"):
        return content.split("```", 1)[1].split("```", 1)[0].strip()
    return content


def _json(value: Any) -> str:
    return json.dumps(value if value is not None else {}, ensure_ascii=False, indent=2, sort_keys=True)
