CREATE TABLE IF NOT EXISTS story_memory_snapshots (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    schema_version INT NOT NULL DEFAULT 1,
    timeline JSONB NOT NULL DEFAULT '[]'::jsonb,
    characters JSONB NOT NULL DEFAULT '[]'::jsonb,
    world JSONB NOT NULL DEFAULT '[]'::jsonb,
    foreshadows JSONB NOT NULL DEFAULT '[]'::jsonb,
    fingerprint_hash VARCHAR(128) NOT NULL DEFAULT '',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_story_memory_snapshots_story UNIQUE (story_id),
    CONSTRAINT ck_story_memory_snapshots_schema_version CHECK (schema_version >= 1),
    CONSTRAINT ck_story_memory_snapshots_timeline_array CHECK (jsonb_typeof(timeline) = 'array'),
    CONSTRAINT ck_story_memory_snapshots_characters_array CHECK (jsonb_typeof(characters) = 'array'),
    CONSTRAINT ck_story_memory_snapshots_world_array CHECK (jsonb_typeof(world) = 'array'),
    CONSTRAINT ck_story_memory_snapshots_foreshadows_array CHECK (jsonb_typeof(foreshadows) = 'array')
);

CREATE INDEX IF NOT EXISTS idx_story_memory_snapshots_story
    ON story_memory_snapshots(story_id);
