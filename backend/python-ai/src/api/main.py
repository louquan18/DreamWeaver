"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from src.core.config import settings
from src.core.logging import setup_logging

from .routes import blueprints, chapters, drafts, health, memory_changes, memory_retrieval, outlines


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    setup_logging()
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="DreamWeaver Multi-Agent 长篇小说创作系统 - AI 服务",
    lifespan=lifespan,
)

# CORS - 允许前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(health.router, tags=["health"])
app.include_router(chapters.router)
app.include_router(blueprints.router)
app.include_router(outlines.router)
app.include_router(drafts.router)
app.include_router(memory_changes.router)
app.include_router(memory_retrieval.router)
