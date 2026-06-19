ALTER TABLE chapters
    ADD COLUMN IF NOT EXISTS workflow_stage VARCHAR(50);

ALTER TABLE chapters
    ADD COLUMN IF NOT EXISTS confirmed_at TIMESTAMPTZ;

UPDATE chapters
SET workflow_stage = CASE
    WHEN status = 'generating' THEN 'draft_generating'
    WHEN status = 'generated' THEN 'draft_ready_for_confirmation'
    WHEN status = 'approved' THEN 'chapter_confirmed'
    WHEN last_generation_id IS NOT NULL THEN 'draft_generated'
    ELSE 'chapter_created'
END
WHERE workflow_stage IS NULL;

UPDATE chapters
SET confirmed_at = updated_at
WHERE status = 'approved'
  AND confirmed_at IS NULL;

ALTER TABLE chapters
    ALTER COLUMN workflow_stage SET NOT NULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'ck_chapters_workflow_stage'
    ) THEN
        ALTER TABLE chapters
            ADD CONSTRAINT ck_chapters_workflow_stage
            CHECK (workflow_stage IN (
                'chapter_created',
                'outline_options_generating',
                'outline_options_generated',
                'outline_confirmed',
                'draft_generating',
                'draft_generated',
                'reviewing',
                'revision_required',
                'draft_ready_for_confirmation',
                'draft_confirmed',
                'memory_extracting',
                'memory_pending_confirmation',
                'memory_confirmed',
                'chapter_confirmed'
            ));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_chapters_story_workflow_stage
    ON chapters(story_id, workflow_stage, chapter_number);
