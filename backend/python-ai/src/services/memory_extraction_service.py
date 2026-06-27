"""Memory extraction service for confirmed chapter drafts."""

import json
from typing import Any

from pydantic import ValidationError

from src.models.llm_client import llm_stream_with_fallback
from src.models.provider import agent_model_chain, agent_temperature
from src.schemas.memory import MemoryExtractionResult
from src.services.memory_extraction_prompt import (
    MemoryExtractionPromptContext,
    build_memory_extraction_messages,
)


class MemoryExtractionGenerationError(RuntimeError):
    """Raised when memory extraction cannot produce a valid structured result."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


MEMORY_EXTRACTION_MAX_TOKENS = 8192
MEMORY_EXTRACTION_RETRY_MAX_TOKENS = 12288


def validate_memory_extraction_request(request: dict[str, Any]) -> dict[str, Any]:
    """Validate Java-supplied context for extracting pending memory changes."""
    if not isinstance(request, dict):
        raise MemoryExtractionGenerationError(
            "INVALID_MEMORY_EXTRACTION_REQUEST",
            "memory extraction request must be a JSON object",
        )

    normalized = dict(request)
    if not str(normalized.get("storyId") or "").strip():
        raise MemoryExtractionGenerationError("STORY_ID_REQUIRED", "storyId is required")
    if not str(normalized.get("chapterId") or "").strip():
        raise MemoryExtractionGenerationError("CHAPTER_ID_REQUIRED", "chapterId is required")
    if not str(normalized.get("sourceGenerationId") or "").strip():
        raise MemoryExtractionGenerationError(
            "SOURCE_GENERATION_ID_REQUIRED",
            "sourceGenerationId is required",
        )
    if not str(normalized.get("confirmedDraft") or "").strip():
        raise MemoryExtractionGenerationError(
            "CONFIRMED_DRAFT_REQUIRED",
            "confirmedDraft is required",
        )

    for key in (
        "story",
        "chapter",
        "blueprint",
        "confirmedOutline",
        "existingMemory",
        "metadata",
        "generationMetadata",
        "reviewMetadata",
        "consistencyMetadata",
        "repairMetadata",
    ):
        if (
            key in normalized
            and normalized[key] is not None
            and not isinstance(normalized[key], dict)
        ):
            raise MemoryExtractionGenerationError(
                f"INVALID_{_constant_case(key)}",
                f"{key} must be a JSON object",
            )

    if "recentChapters" in normalized and normalized["recentChapters"] is not None:
        if not isinstance(normalized["recentChapters"], list):
            raise MemoryExtractionGenerationError(
                "INVALID_RECENT_CHAPTERS",
                "recentChapters must be a list",
            )

    normalized["storyId"] = str(normalized["storyId"]).strip()
    normalized["chapterId"] = str(normalized["chapterId"]).strip()
    normalized["sourceGenerationId"] = str(normalized["sourceGenerationId"]).strip()
    normalized["confirmedDraft"] = str(normalized["confirmedDraft"]).strip()
    normalized.setdefault("story", {})
    normalized.setdefault("chapter", {})
    normalized.setdefault("blueprint", {})
    normalized.setdefault("confirmedOutline", {})
    normalized.setdefault("recentChapters", [])
    normalized.setdefault("existingMemory", {})
    normalized.setdefault("generationMetadata", {})
    normalized.setdefault("reviewMetadata", {})
    normalized.setdefault("consistencyMetadata", {})
    normalized.setdefault("repairMetadata", {})
    return normalized


def build_memory_extraction_messages_from_request(
    request: dict[str, Any],
) -> list[dict[str, str]]:
    """Build Memory Extraction Agent messages from the Java request payload."""
    payload = validate_memory_extraction_request(request)
    return build_memory_extraction_messages(
        MemoryExtractionPromptContext(
            story_id=payload["storyId"],
            chapter_id=payload["chapterId"],
            source_generation_id=payload["sourceGenerationId"],
            story=payload.get("story") or {},
            chapter=payload.get("chapter") or {},
            blueprint=payload.get("blueprint") or {},
            confirmed_outline=payload.get("confirmedOutline") or {},
            recent_chapters=payload.get("recentChapters") or [],
            existing_memory=payload.get("existingMemory") or {},
            generation_metadata=payload.get("generationMetadata") or {},
            review_metadata=payload.get("reviewMetadata") or {},
            consistency_metadata=payload.get("consistencyMetadata") or {},
            repair_metadata=payload.get("repairMetadata") or {},
            confirmed_draft=payload["confirmedDraft"],
        )
    )


async def extract_memory_from_confirmed_draft(
    request: dict[str, Any],
) -> MemoryExtractionResult:
    """Extract pending memory changes from a confirmed draft via the reviewer model profile."""
    payload = validate_memory_extraction_request(request)
    messages = build_memory_extraction_messages_from_request(payload)
    raw_response = await _invoke_memory_extraction_agent(
        messages,
        max_tokens=MEMORY_EXTRACTION_MAX_TOKENS,
    )
    try:
        result = parse_memory_extraction_response(raw_response)
    except MemoryExtractionGenerationError as exc:
        if not _should_retry_invalid_json(exc, raw_response):
            raise
        raw_response = await _invoke_memory_extraction_agent(
            messages,
            max_tokens=MEMORY_EXTRACTION_RETRY_MAX_TOKENS,
        )
        result = parse_memory_extraction_response(raw_response)

    _assert_result_matches_request(result, payload)
    return result


async def _invoke_memory_extraction_agent(
    messages: list[dict[str, str]],
    *,
    max_tokens: int,
) -> str:
    raw_response = ""
    async for token in llm_stream_with_fallback(
        messages,
        models=agent_model_chain("memory_extract"),
        max_tokens=max_tokens,
        temperature=agent_temperature("memory_extract"),
    ):
        raw_response += token
    return raw_response


def parse_memory_extraction_response(raw_response: str) -> MemoryExtractionResult:
    """Parse and validate the Memory Extraction Agent JSON-only response."""
    content = _strip_json_fence(raw_response)
    if not content:
        raise MemoryExtractionGenerationError(
            "EMPTY_MEMORY_EXTRACTION_RESPONSE",
            "Memory extraction agent returned an empty response",
        )
    try:
        data = json.loads(content)
    except json.JSONDecodeError as exc:
        raise MemoryExtractionGenerationError(
            "INVALID_MEMORY_EXTRACTION_JSON",
            f"Memory extraction agent returned invalid JSON: {exc.msg}",
        ) from exc

    if not isinstance(data, dict):
        raise MemoryExtractionGenerationError(
            "INVALID_MEMORY_EXTRACTION_JSON_OBJECT",
            "Memory extraction agent must return one JSON object",
        )

    try:
        return MemoryExtractionResult.model_validate(data)
    except ValidationError as exc:
        raise MemoryExtractionGenerationError(
            "INVALID_MEMORY_EXTRACTION_SCHEMA",
            f"Memory extraction response failed schema validation: {exc}",
        ) from exc


def _strip_json_fence(raw_response: str) -> str:
    content = (raw_response or "").strip()
    if content.lower().startswith("```json"):
        return content.split("\n", 1)[1].split("```", 1)[0].strip()
    if content.startswith("```"):
        return content.split("```", 1)[1].split("```", 1)[0].strip()
    if not content.startswith("{"):
        extracted = _extract_first_json_object(content)
        if extracted:
            return extracted
    return content


def _extract_first_json_object(content: str) -> str | None:
    start = content.find("{")
    if start == -1:
        return None

    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(content)):
        char = content[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue

        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[start : index + 1].strip()
    return None


def _should_retry_invalid_json(
    exc: MemoryExtractionGenerationError,
    raw_response: str,
) -> bool:
    if exc.code != "INVALID_MEMORY_EXTRACTION_JSON":
        return False

    content = _strip_json_fence(raw_response)
    if content and not content.rstrip().endswith("}"):
        return True

    truncation_markers = (
        "Unterminated string",
        "Expecting ',' delimiter",
        "Expecting property name enclosed in double quotes",
    )
    return any(marker in exc.message for marker in truncation_markers)


def _assert_result_matches_request(
    result: MemoryExtractionResult,
    request: dict[str, Any],
) -> None:
    expected = {
        "storyId": request["storyId"],
        "chapterId": request["chapterId"],
        "sourceGenerationId": request["sourceGenerationId"],
    }
    actual = result.model_dump(by_alias=True)
    mismatched = [
        key
        for key, expected_value in expected.items()
        if actual.get(key) != expected_value
    ]
    if mismatched:
        raise MemoryExtractionGenerationError(
            "MEMORY_EXTRACTION_RESULT_MISMATCH",
            f"Memory extraction result mismatched request fields: {', '.join(mismatched)}",
        )


def _constant_case(value: str) -> str:
    result: list[str] = []
    for index, char in enumerate(value):
        if char.isupper() and index > 0:
            result.append("_")
        result.append(char.upper())
    return "".join(result)
