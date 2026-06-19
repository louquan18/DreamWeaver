CREATE TABLE IF NOT EXISTS novel_blueprints (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    source_prompt TEXT,
    premise TEXT NOT NULL,
    genre VARCHAR(50),
    tone VARCHAR(100),
    protagonist JSONB NOT NULL DEFAULT '{}'::jsonb,
    main_thread JSONB NOT NULL DEFAULT '{}'::jsonb,
    core_conflict JSONB NOT NULL DEFAULT '{}'::jsonb,
    world_seed JSONB NOT NULL DEFAULT '{}'::jsonb,
    writing_preferences JSONB NOT NULL DEFAULT '{}'::jsonb,
    locked_facts JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'generated',
    confirmed_at TIMESTAMPTZ,
    superseded_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_novel_blueprint_status
        CHECK (status IN ('generated', 'confirmed', 'superseded')),
    CONSTRAINT ck_novel_blueprint_locked_facts_array
        CHECK (jsonb_typeof(locked_facts) = 'array'),
    CONSTRAINT ck_novel_blueprint_confirmed_at
        CHECK (
            (status = 'confirmed' AND confirmed_at IS NOT NULL)
            OR (status <> 'confirmed')
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_novel_blueprints_one_confirmed_per_story
    ON novel_blueprints(story_id)
    WHERE status = 'confirmed';

CREATE INDEX IF NOT EXISTS idx_novel_blueprints_story_created
    ON novel_blueprints(story_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_novel_blueprints_story_status_created
    ON novel_blueprints(story_id, status, created_at DESC);
