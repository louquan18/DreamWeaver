CREATE TABLE IF NOT EXISTS chapter_memory_summaries (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    chapter_number INT NOT NULL,
    title VARCHAR(200),
    summary TEXT NOT NULL,
    source_draft_hash VARCHAR(128) NOT NULL,
    source_generation_id UUID REFERENCES chapter_generations(id) ON DELETE SET NULL,
    extractor_version VARCHAR(100),
    extraction_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_chapter_memory_summaries_story_chapter UNIQUE (story_id, chapter_id),
    CONSTRAINT ck_chapter_memory_summaries_summary CHECK (length(summary) > 0),
    CONSTRAINT ck_chapter_memory_summaries_source_draft_hash CHECK (length(source_draft_hash) > 0)
);

CREATE INDEX IF NOT EXISTS idx_chapter_memory_summaries_story_number
    ON chapter_memory_summaries(story_id, chapter_number);

CREATE INDEX IF NOT EXISTS idx_chapter_memory_summaries_chapter
    ON chapter_memory_summaries(chapter_id);
