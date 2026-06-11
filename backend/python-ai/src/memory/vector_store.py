"""Chroma 向量存储集成

用于章节摘要和原文段落的语义检索。
- 摘要级检索：快速粗粒度，用于上下文组装
- 原文段落级检索：精确细粒度，用于一致性深度检查
"""

from typing import Any

from loguru import logger

from src.core.config import settings

# Chroma 客户端（延迟初始化）
_chroma_client = None


def _get_chroma_client():
    """获取 Chroma 客户端（单例）"""
    global _chroma_client
    if _chroma_client is None:
        try:
            import chromadb

            _chroma_client = chromadb.HttpClient(
                host=settings.chroma_host,
                port=settings.chroma_port,
            )
            logger.info(f"[VectorStore] Chroma connected: {settings.chroma_host}:{settings.chroma_port}")
        except Exception as e:
            logger.warning(f"[VectorStore] Chroma unavailable: {e}")
            _chroma_client = None
    return _chroma_client


def _get_or_create_collection(story_id: str):
    """获取或创建小说的向量集合"""
    client = _get_chroma_client()
    if client is None:
        return None

    collection_name = f"novel_{story_id.replace('-', '_')}"
    try:
        return client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    except Exception as e:
        logger.warning(f"[VectorStore] Collection error: {e}")
        return None


async def add_chapter_summary(
    story_id: str,
    chapter_number: int,
    summary: str,
    metadata: dict[str, Any] | None = None,
) -> bool:
    """
    将章节摘要存入向量库

    Args:
        story_id: 小说 ID
        chapter_number: 章节号
        summary: 章节摘要文本
        metadata: 附加元数据

    Returns:
        是否成功
    """
    collection = _get_or_create_collection(story_id)
    if collection is None:
        return False

    doc_id = f"chapter_{chapter_number}"
    meta = {
        "chapter_number": chapter_number,
        "story_id": story_id,
        **(metadata or {}),
    }

    try:
        collection.upsert(
            ids=[doc_id],
            documents=[summary],
            metadatas=[meta],
        )
        logger.debug(f"[VectorStore] Added summary for chapter {chapter_number}")
        return True
    except Exception as e:
        logger.warning(f"[VectorStore] Add failed: {e}")
        return False


async def search_relevant_chapters(
    story_id: str,
    query: str,
    k: int = 5,
) -> list[dict[str, Any]]:
    """
    语义检索相关章节摘要

    Args:
        story_id: 小说 ID
        query: 检索查询
        k: 返回数量

    Returns:
        [{chapter_number, summary, distance}]
    """
    collection = _get_or_create_collection(story_id)
    if collection is None:
        return []

    try:
        results = collection.query(
            query_texts=[query],
            n_results=min(k, collection.count() or 1),
        )

        chapters = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                chapters.append({
                    "chapter_number": meta.get("chapter_number", 0),
                    "summary": doc,
                    "distance": distance,
                })

        logger.debug(f"[VectorStore] Found {len(chapters)} relevant chapters")
        return chapters

    except Exception as e:
        logger.warning(f"[VectorStore] Search failed: {e}")
        return []


async def get_collection_stats(story_id: str) -> dict[str, Any]:
    """获取向量集合统计"""
    collection = _get_or_create_collection(story_id)
    if collection is None:
        return {"available": False}

    try:
        count = collection.count()
        return {
            "available": True,
            "document_count": count,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}


# ========== 原文段落级存储（支持深度语义检索） ==========


def _split_into_chunks(
    text: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> list[str]:
    """
    将文本按字符数分段，支持 overlap 重叠以避免语义截断。

    Args:
        text: 原文文本
        chunk_size: 每段目标字符数
        overlap: 相邻段重叠字符数

    Returns:
        分段后的文本列表
    """
    if not text:
        return []

    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        if chunk.strip():
            chunks.append(chunk.strip())
        start = end - overlap
        # 避免最后一段过短导致死循环
        if end >= len(text):
            break

    return chunks


async def add_chapter_fulltext(
    story_id: str,
    chapter_number: int,
    content: str,
    chunk_size: int = 500,
    overlap: int = 100,
) -> bool:
    """
    将章节原文的分段 embedding 存入向量库，用于段落级深度检索。

    每个段落作为一个独立 document 存储，metadata 包含章节号和段落序号。
    使用独立 collection（{story_id}_fulltext），与摘要 collection 隔离。

    Args:
        story_id: 小说 ID
        chapter_number: 章节号
        content: 章节原文
        chunk_size: 每段目标字符数
        overlap: 相邻段重叠字符数

    Returns:
        是否成功
    """
    collection = _get_or_create_collection(f"{story_id}_fulltext")
    if collection is None:
        return False

    paragraphs = _split_into_chunks(content, chunk_size=chunk_size, overlap=overlap)
    if not paragraphs:
        return False

    # 先删除该章节的旧段落（避免重复 upsert 越积越多）
    try:
        existing = collection.get(where={"chapter_number": chapter_number})
        if existing and existing["ids"]:
            collection.delete(ids=existing["ids"])
    except Exception:
        pass  # 首次写入时无旧数据，忽略

    ids = [f"ch{chapter_number}_p{i}" for i in range(len(paragraphs))]
    metadatas = [
        {"chapter_number": chapter_number, "paragraph_index": i}
        for i in range(len(paragraphs))
    ]

    try:
        collection.upsert(ids=ids, documents=paragraphs, metadatas=metadatas)
        logger.debug(
            f"[VectorStore] Added {len(paragraphs)} paragraphs for chapter {chapter_number}"
        )
        return True
    except Exception as e:
        logger.warning(f"[VectorStore] Fulltext add failed: {e}")
        return False


async def search_relevant_paragraphs(
    story_id: str,
    query: str,
    k: int = 5,
    chapter_range: tuple[int, int] | None = None,
) -> list[dict[str, Any]]:
    """
    深度检索：在原文段落级别做语义搜索。

    用于一致性检查时精确定位相关段落，替代粗粒度的摘要级检索。

    Args:
        story_id: 小说 ID
        query: 检索查询
        k: 返回数量
        chapter_range: 可选，限定章节范围 (start, end)

    Returns:
        [{chapter_number, paragraph_index, text, distance}]
    """
    collection = _get_or_create_collection(f"{story_id}_fulltext")
    if collection is None:
        return []

    try:
        count = collection.count()
        if count == 0:
            return []

        where_filter = None
        if chapter_range:
            where_filter = {
                "$and": [
                    {"chapter_number": {"$gte": chapter_range[0]}},
                    {"chapter_number": {"$lte": chapter_range[1]}},
                ]
            }

        results = collection.query(
            query_texts=[query],
            n_results=min(k, count),
            where=where_filter,
        )

        paragraphs = []
        if results and results["documents"]:
            for i, doc in enumerate(results["documents"][0]):
                meta = results["metadatas"][0][i] if results["metadatas"] else {}
                distance = results["distances"][0][i] if results["distances"] else 0
                paragraphs.append({
                    "chapter_number": meta.get("chapter_number", 0),
                    "paragraph_index": meta.get("paragraph_index", 0),
                    "text": doc,
                    "distance": distance,
                })

        logger.debug(f"[VectorStore] Found {len(paragraphs)} relevant paragraphs")
        return paragraphs

    except Exception as e:
        logger.warning(f"[VectorStore] Paragraph search failed: {e}")
        return []


async def get_fulltext_stats(story_id: str) -> dict[str, Any]:
    """获取原文段落集合统计"""
    collection = _get_or_create_collection(f"{story_id}_fulltext")
    if collection is None:
        return {"available": False}

    try:
        count = collection.count()
        return {
            "available": True,
            "paragraph_count": count,
        }
    except Exception as e:
        return {"available": False, "error": str(e)}
