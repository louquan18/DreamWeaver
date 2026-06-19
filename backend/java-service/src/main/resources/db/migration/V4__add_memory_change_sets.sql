CREATE TABLE IF NOT EXISTS memory_change_sets (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    source_generation_id UUID NOT NULL REFERENCES chapter_generations(id) ON DELETE CASCADE,
    status VARCHAR(32) NOT NULL DEFAULT 'pending',
    schema_version INT NOT NULL DEFAULT 1,
    timeline_changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    character_changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    world_changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    foreshadow_changes JSONB NOT NULL DEFAULT '[]'::jsonb,
    conflicts JSONB NOT NULL DEFAULT '[]'::jsonb,
    base_memory_fingerprint JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_draft_hash VARCHAR(128) NOT NULL,
    extraction_metadata JSONB,
    apply_result JSONB,
    created_by UUID,
    confirmed_by UUID,
    rejected_by UUID,
    confirmed_at TIMESTAMPTZ,
    rejected_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_memory_change_sets_status
        CHECK (status IN ('pending', 'confirmed', 'rejected')),
    CONSTRAINT ck_memory_change_sets_schema_version
        CHECK (schema_version >= 1),
    CONSTRAINT ck_memory_change_sets_source_draft_hash
        CHECK (length(source_draft_hash) > 0),
    CONSTRAINT uq_memory_change_sets_story_chapter_generation
        UNIQUE (story_id, chapter_id, source_generation_id)
);

CREATE INDEX IF NOT EXISTS idx_memory_change_sets_story_chapter
    ON memory_change_sets(story_id, chapter_id);

CREATE INDEX IF NOT EXISTS idx_memory_change_sets_generation
    ON memory_change_sets(source_generation_id);

CREATE INDEX IF NOT EXISTS idx_memory_change_sets_status
    ON memory_change_sets(status);

CREATE INDEX IF NOT EXISTS idx_memory_change_sets_conflicts
    ON memory_change_sets USING GIN(conflicts);
