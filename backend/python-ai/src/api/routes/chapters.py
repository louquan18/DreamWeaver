"""章节生成 API"""

from fastapi import APIRouter

router = APIRouter(prefix="/api/ai/chapters", tags=["chapters"])


@router.post("/generate")
async def generate_chapter():
    """生成章节（同步）- 待实现"""
    return {"message": "TODO: implement chapter generation"}


@router.post("/generate-stream")
async def generate_chapter_stream():
    """生成章节（SSE 流式）- 待实现"""
    return {"message": "TODO: implement SSE streaming"}
