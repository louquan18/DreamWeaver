"""Chapter generation API with token-level SSE streaming."""

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from src.workflows import create_initial_state, default_app
from src.workflows.token_buffer import cleanup_buffer, read_tokens_with_done_sync

router = APIRouter(prefix="/api/ai/chapters", tags=["chapters"])


@router.post("/generate")
async def generate_chapter(
    story_id: str = Query(..., description="Story ID"),
    chapter_id: str = Query(..., description="Chapter ID"),
    user_id: str = Query("", description="User ID"),
):
    """Generate a chapter with the full workflow and return the final state."""
    state = create_initial_state(story_id, chapter_id, user_id)
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}
    final_state = await default_app.ainvoke(state, config)
    draft = final_state.get("generated_draft", "")
    return {
        "story_id": story_id,
        "chapter_id": chapter_id,
        "draft": draft,
        "word_count": len(draft),
        "execution_history": final_state.get("execution_history", []),
    }


@router.get("/generate-stream")
async def generate_chapter_stream(
    story_id: str = Query(..., description="Story ID"),
    chapter_id: str = Query(..., description="Chapter ID"),
    user_id: str = Query("", description="User ID"),
    generation_id: str | None = Query(None, description="Java generation ID"),
):
    """Generate a chapter draft and stream tokens to Java.

    MVP boundary: Java owns generation records and chapter content. This Python
    SSE endpoint returns as soon as the draft token stream completes, instead of
    waiting for slower downstream workflow nodes.
    """

    async def event_stream():
        thread_id = generation_id or f"{story_id}-{chapter_id}"
        state = create_initial_state(story_id, chapter_id, user_id)
        # 把 SSE token buffer 的 key 显式传入 state，确保 writer 写端与此处读端使用同一 key
        state["metadata"] = {**state.get("metadata", {}), "sse_thread_id": thread_id}
        config = {"configurable": {"thread_id": thread_id}}

        yield _sse("node_start", {"node": "load_runtime_context", "progress": 5})
        yield _sse("node_end", {"node": "load_runtime_context", "progress": 5})
        yield _sse("node_start", {"node": "novel_context", "progress": 15})
        yield _sse("node_end", {"node": "novel_context", "progress": 15})
        yield _sse("node_start", {"node": "plan_chapter", "progress": 30})

        loop = asyncio.get_event_loop()
        workflow_future = loop.run_in_executor(
            None,
            _run_workflow_sync,
            state,
            config,
        )

        yield _sse("node_end", {"node": "plan_chapter", "progress": 30})
        yield _sse("node_start", {"node": "generate_draft", "progress": 50})

        token_count = 0
        draft_parts: list[str] = []
        stream_done = False

        # 心跳：planner 等慢节点期间可能数十秒无 token，需周期性发字节
        # 防止 nginx proxy_read_timeout / 代理空闲超时掐断 SSE 连接
        idle_cycles = 0
        heartbeat_cycles = 200  # 200 * 0.05s ≈ 10s

        while not stream_done:
            tokens, token_stream_done = read_tokens_with_done_sync(thread_id)
            for token in tokens:
                draft_parts.append(token)
                token_count += 1
                yield _sse("token", {"content": token})

            if tokens:
                idle_cycles = 0

            if token_stream_done:
                stream_done = True
                break

            if workflow_future.done() and not tokens:
                tokens, token_stream_done = read_tokens_with_done_sync(thread_id)
                for token in tokens:
                    draft_parts.append(token)
                    token_count += 1
                    yield _sse("token", {"content": token})

                if workflow_future.exception() is not None and not draft_parts:
                    exc = workflow_future.exception()
                    logger.error(f"[SSE] Workflow failed before streaming draft: {exc}")
                    yield _sse("error", {"message": str(exc)})
                    cleanup_buffer(thread_id)
                    return

                stream_done = True
                break

            idle_cycles += 1
            if idle_cycles >= heartbeat_cycles:
                idle_cycles = 0
                yield ": keepalive\n\n"

            await asyncio.sleep(0.05)

        final_draft = "".join(draft_parts)
        yield _sse("node_end", {"node": "generate_draft", "progress": 50})
        yield _sse(
            "done",
            {
                "story_id": story_id,
                "chapter_id": chapter_id,
                "saved_chapter_id": None,
                "draft": final_draft,
                "word_count": len(final_draft),
                "tokens_streamed": token_count,
            },
        )

        workflow_future.add_done_callback(
            lambda future: _log_background_workflow_result(future, thread_id)
        )

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _run_workflow_sync(state: dict, config: dict) -> dict:
    """Run the workflow inside the executor thread."""
    return asyncio.run(default_app.ainvoke(state, config))


def _log_background_workflow_result(future: asyncio.Future, thread_id: str) -> None:
    """Observe background workflow failures and release the token buffer."""
    try:
        future.result()
    except Exception as exc:
        logger.warning(f"[SSE] Background workflow failed after draft stream: {exc}")
    finally:
        cleanup_buffer(thread_id)


def _sse(event: str, data: dict[str, Any]) -> str:
    """Format one SSE event."""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
