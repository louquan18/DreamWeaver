CREATE TABLE IF NOT EXISTS chapter_outline_options (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    option_group_id UUID NOT NULL,
    option_code VARCHAR(1) NOT NULL,
    option_type VARCHAR(30) NOT NULL,
    title_candidates JSONB NOT NULL DEFAULT '[]'::jsonb,
    chapter_goal TEXT NOT NULL,
    story_summary TEXT NOT NULL,
    scene_outline JSONB NOT NULL DEFAULT '[]'::jsonb,
    characters_involved JSONB NOT NULL DEFAULT '[]'::jsonb,
    conflict JSONB NOT NULL DEFAULT '{}'::jsonb,
    highlight_moment TEXT,
    foreshadow_actions JSONB NOT NULL DEFAULT '[]'::jsonb,
    memory_references JSONB NOT NULL DEFAULT '[]'::jsonb,
    why_this_plan TEXT,
    ending_hook TEXT,
    risk_notes JSONB NOT NULL DEFAULT '[]'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'generated',
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_chapter_outline_option_code
        CHECK (option_code IN ('A', 'B', 'C')),
    CONSTRAINT ck_chapter_outline_option_type
        CHECK (option_type IN ('steady', 'conflict', 'foreshadow')),
    CONSTRAINT ck_chapter_outline_option_status
        CHECK (status IN ('generated', 'selected', 'discarded', 'superseded')),
    CONSTRAINT uq_chapter_outline_option_group_code
        UNIQUE (chapter_id, option_group_id, option_code),
    CONSTRAINT uq_chapter_outline_option_group_type
        UNIQUE (chapter_id, option_group_id, option_type)
);

CREATE INDEX IF NOT EXISTS idx_chapter_outline_options_chapter_created
    ON chapter_outline_options(story_id, chapter_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chapter_outline_options_group
    ON chapter_outline_options(chapter_id, option_group_id);

CREATE INDEX IF NOT EXISTS idx_chapter_outline_options_status_created
    ON chapter_outline_options(status, created_at DESC);

CREATE TABLE IF NOT EXISTS chapter_outlines (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    story_id UUID NOT NULL REFERENCES stories(id) ON DELETE CASCADE,
    chapter_id UUID NOT NULL REFERENCES chapters(id) ON DELETE CASCADE,
    source_option_ids JSONB NOT NULL DEFAULT '[]'::jsonb,
    user_feedback TEXT,
    final_outline JSONB NOT NULL DEFAULT '{}'::jsonb,
    status VARCHAR(20) NOT NULL DEFAULT 'draft',
    confirmed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT ck_chapter_outline_status
        CHECK (status IN ('draft', 'confirmed', 'superseded')),
    CONSTRAINT ck_chapter_outline_confirmed_at
        CHECK (
            (status = 'confirmed' AND confirmed_at IS NOT NULL)
            OR status <> 'confirmed'
        )
);

CREATE UNIQUE INDEX IF NOT EXISTS uq_chapter_outlines_one_confirmed
    ON chapter_outlines(chapter_id)
    WHERE status = 'confirmed';

CREATE INDEX IF NOT EXISTS idx_chapter_outlines_chapter_created
    ON chapter_outlines(story_id, chapter_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_chapter_outlines_status_created
    ON chapter_outlines(status, created_at DESC);
