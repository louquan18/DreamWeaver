-- DreamWeaver Database Initialization
-- 基础表结构将在 M1-T4 中通过 Alembic 迁移创建

-- 启用 UUID 扩展
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 启用 JSONB 索引支持
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
