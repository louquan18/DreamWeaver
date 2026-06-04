"""章节生成 API + SSE 流式输出"""

import json
from typing import Any

from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from loguru import logger

from src.workflows import create_initial_state, default_app

router = APIRouter(prefix="/api/ai/chapters", tags=["chapters"])


@router.post("/generate")
async def generate_chapter(
    story_id: str = Query(..., description="小说 ID"),
    chapter_id: str = Query(..., description="章节 ID"),
    user_id: str = Query("", description="用户 ID"),
):
    """
    生成章节（同步）

    等待完整工作流执行完毕后返回结果。
    """
    state = create_initial_state(story_id, chapter_id, user_id)
    config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}

    final_state = await default_app.ainvoke(state, config)

    return {
        "story_id": story_id,
        "chapter_id": chapter_id,
        "draft": final_state.get("generated_draft", ""),
        "word_count": len(final_state.get("generated_draft", "")),
        "execution_history": final_state.get("execution_history", []),
    }


@router.post("/generate-stream")
async def generate_chapter_stream(
    story_id: str = Query(..., description="小说 ID"),
    chapter_id: str = Query(..., description="章节 ID"),
    user_id: str = Query("", description="用户 ID"),
):
    """
    生成章节（SSE 流式输出）

    使用 Server-Sent Events 实时推送工作流进度：
      - node_start / node_end: 节点执行事件
      - token: LLM 输出 token（Writer Agent 阶段）
      - progress: 整体进度百分比
      - done: 完成事件
      - error: 错误事件
    """

    async def event_stream():
        state = create_initial_state(story_id, chapter_id, user_id)
        config = {"configurable": {"thread_id": f"{story_id}-{chapter_id}"}}

        # 节点进度映射
        node_progress = {
            "load_runtime_context": 5,
            "novel_context": 15,
            "plan_chapter": 30,
            "generate_draft": 50,
            "check_consistency": 70,
            "review": 80,
            "rewrite": 85,
            "commit": 100,
        }

        try:
            async for event in default_app.astream_events(state, config, version="v1"):
                event_type = event.get("event", "")
                event_name = event.get("name", "")

                # 节点开始
                if event_type == "on_chain_start" and event_name in node_progress:
                    progress = node_progress[event_name]
                    yield _sse("node_start", {"node": event_name, "progress": progress})

                # LLM Token 流（Writer Agent 阶段）
                elif event_type == "on_llm_stream":
                    chunk = event.get("data", {}).get("chunk", None)
                    if chunk and hasattr(chunk, "content") and chunk.content:
                        yield _sse("token", {"content": chunk.content})

                # 节点结束
                elif event_type == "on_chain_end" and event_name in node_progress:
                    progress = node_progress[event_name]
                    yield _sse("node_end", {"node": event_name, "progress": progress})

            # 完成
            yield _sse("done", {
                "story_id": story_id,
                "chapter_id": chapter_id,
            })

        except Exception as e:
            logger.error(f"[SSE] Stream error: {e}")
            yield _sse("error", {"message": str(e)})

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


def _sse(event: str, data: dict[str, Any]) -> str:
    """格式化 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
