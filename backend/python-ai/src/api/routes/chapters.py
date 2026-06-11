"""章节生成 API + Token 级 SSE 流式输出"""

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
    story_id: str = Query(..., description="小说 ID"),
    chapter_id: str = Query(..., description="章节 ID"),
    user_id: str = Query("", description="用户 ID"),
):
    """生成章节（同步）"""
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


@router.get("/generate-stream")
async def generate_chapter_stream(
    story_id: str = Query(..., description="小说 ID"),
    chapter_id: str = Query(..., description="章节 ID"),
    user_id: str = Query("", description="用户 ID"),
):
    """
    生成章节（Token 级 SSE 流式输出）

    工作流在线程池中运行，SSE 端点在主事件循环中读取 token 流。
    """

    async def event_stream():
        thread_id = f"{story_id}-{chapter_id}"
        state = create_initial_state(story_id, chapter_id, user_id)
        config = {"configurable": {"thread_id": thread_id}}

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

        # 发送前置节点事件
        yield _sse("node_start", {"node": "load_runtime_context", "progress": 5})
        yield _sse("node_end", {"node": "load_runtime_context", "progress": 5})
        yield _sse("node_start", {"node": "novel_context", "progress": 15})
        yield _sse("node_end", {"node": "novel_context", "progress": 15})
        yield _sse("node_start", {"node": "plan_chapter", "progress": 30})

        # 工作流在线程池中运行（不阻塞事件循环）
        loop = asyncio.get_event_loop()
        workflow_future = loop.run_in_executor(
            None,
            _run_workflow_sync,
            state,
            config,
        )

        yield _sse("node_end", {"node": "plan_chapter", "progress": 30})
        yield _sse("node_start", {"node": "generate_draft", "progress": 50})

        # 轮询读取 token（线程安全的非阻塞读取）
        token_count = 0
        done = False
        while not done:
            # 读取所有已缓冲的 tokens
            tokens, stream_done = read_tokens_with_done_sync(thread_id)
            for token in tokens:
                yield _sse("token", {"content": token})
                token_count += 1

            if stream_done:
                done = True

            # 检查工作流是否完成且 buffer 已空
            if workflow_future.done() and not tokens:
                # 再读一次确保没有遗漏
                tokens, _ = read_tokens_with_done_sync(thread_id)
                for token in tokens:
                    yield _sse("token", {"content": token})
                    token_count += 1
                done = True

            if not done:
                await asyncio.sleep(0.05)  # 50ms 轮询间隔

        yield _sse("node_end", {"node": "generate_draft", "progress": 50})

        # 等待工作流完成
        try:
            final_state = await workflow_future
        except Exception as e:
            logger.error(f"[SSE] Workflow error: {e}")
            yield _sse("error", {"message": str(e)})
            cleanup_buffer(thread_id)
            return

        execution_history = final_state.get("execution_history", [])

        # 发送后续节点事件
        for node_name in ["check_consistency", "review", "rewrite", "commit"]:
            if node_name in execution_history:
                progress = node_progress.get(node_name, 0)
                yield _sse("node_start", {"node": node_name, "progress": progress})
                yield _sse("node_end", {"node": node_name, "progress": progress})

        # 保存章节到数据库
        final_draft = final_state.get("generated_draft", "")
        saved_chapter_id = None
        try:
            from src.core.database import async_session_factory
            from src.repositories.chapter_repository import ChapterRepository
            from src.repositories.story_repository import StoryRepository
            from src.schemas.chapter import ChapterCreate

            async with async_session_factory() as db:
                chapter_repo = ChapterRepository(db)
                story_repo = StoryRepository(db)

                # 确保 story 存在
                import uuid as uuid_mod
                story_uuid = uuid_mod.UUID(story_id) if "-" in story_id else uuid_mod.uuid5(uuid_mod.NAMESPACE_DNS, story_id)
                story = await story_repo.get_by_id(story_uuid)
                if not story:
                    from src.schemas.story import StoryCreate
                    story = await story_repo.create(
                        StoryCreate(title=f"Story {story_id[:8]}"),
                        user_id=uuid_mod.UUID("00000000-0000-0000-0000-000000000001"),
                    )

                # 保存章节
                chapter_data = ChapterCreate(
                    chapter_number=1,  # TODO: 从 state 获取
                    title=f"Chapter {chapter_id[:8]}",
                )
                chapter = await chapter_repo.create(chapter_data, story.id)
                # 更新内容
                await chapter_repo.update(chapter.id, type("U", (), {
                    "model_dump": lambda self, **kw: {
                        "content": final_draft,
                        "word_count": len(final_draft),
                        "status": "completed",
                    },
                    "model_dump_json": lambda self, **kw: "{}",
                })())
                saved_chapter_id = str(chapter.id)
                logger.info(f"[SSE] Chapter saved: {saved_chapter_id}")
        except Exception as e:
            logger.warning(f"[SSE] Failed to save chapter: {e}")

        # 完成
        yield _sse("done", {
            "story_id": story_id,
            "chapter_id": chapter_id,
            "saved_chapter_id": saved_chapter_id,
            "draft": final_draft,
            "word_count": len(final_draft),
            "tokens_streamed": token_count,
        })

        cleanup_buffer(thread_id)

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
    """在线程池中运行工作流（同步包装）"""
    return asyncio.run(default_app.ainvoke(state, config))


def _sse(event: str, data: dict[str, Any]) -> str:
    """格式化 SSE 事件"""
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"
