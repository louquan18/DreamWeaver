CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS stories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    title VARCHAR(200) NOT NULL,
    description TEXT,
    genre VARCHAR(50),
    target_words INT,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_stories_user_id ON stories(user_id);
CREATE INDEX IF NOT EXISTS idx_stories_genre ON stories(genre);

CREATE TABLE IF NOT EXISTS chapters (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title VARCHAR(200),
    content TEXT,
    content_url TEXT,
    word_count INT,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_chapter_story_number UNIQUE (story_id, chapter_number)
);

CREATE INDEX IF NOT EXISTS idx_chapters_story_id ON chapters(story_id);

ALTER TABLE chapters
    ADD COLUMN IF NOT EXISTS content TEXT;

CREATE TABLE IF NOT EXISTS chapter_generations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    user_id UUID NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'queued',
    request JSONB NOT NULL DEFAULT '{}'::jsonb,
    draft TEXT,
    draft_url TEXT,
    word_count INT,
    model_profile VARCHAR(50),
    model_name VARCHAR(100),
    execution_history JSONB NOT NULL DEFAULT '[]'::jsonb,
    consistency_report JSONB,
    review_report JSONB,
    checkpoint_id UUID,
    error_message TEXT,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_chapter_generation_status
        CHECK (status IN ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
    CONSTRAINT ck_chapter_generation_word_count
        CHECK (word_count IS NULL OR word_count >= 0)
);

CREATE INDEX IF NOT EXISTS idx_chapter_generations_chapter_created
    ON chapter_generations(story_id, chapter_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chapter_generations_status_created
    ON chapter_generations(status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chapter_generations_user_created
    ON chapter_generations(user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chapter_generations_request
    ON chapter_generations USING GIN(request);

ALTER TABLE chapters
    ADD COLUMN IF NOT EXISTS last_generation_id UUID NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'fk_chapters_last_generation'
    ) THEN
        ALTER TABLE chapters
            ADD CONSTRAINT fk_chapters_last_generation
            FOREIGN KEY (last_generation_id)
            REFERENCES chapter_generations(id)
            ON DELETE SET NULL;
    END IF;
END $$;
