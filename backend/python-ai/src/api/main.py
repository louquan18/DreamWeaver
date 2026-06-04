"""FastAPI 应用入口"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from src.core.config import settings
from src.core.logging import setup_logging

from .routes import chapters, health


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

# 注册路由
app.include_router(health.router, tags=["health"])
app.include_router(chapters.router)
