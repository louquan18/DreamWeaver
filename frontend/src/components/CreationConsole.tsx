import { useMemo, useState, type FormEvent } from 'react'
import { createChapter } from '../services/api'
import type { Chapter, Story } from '../types'
import './CreationConsole.css'

interface CreationConsoleProps {
  selectedStory: Story | null
  selectedChapter: Chapter | null
  chapters: Chapter[]
  loading?: boolean
  onGenerate: (storyId: string, chapterId: string) => void
  onCancel: () => void
  onReset: () => void
  onChapterCreated: (chapter: Chapter) => void
  onChapterSelected: (chapterId: string) => void
  status: 'idle' | 'connecting' | 'generating' | 'done' | 'error'
  errorMessage: string
}

export function CreationConsole({
  selectedStory,
  selectedChapter,
  chapters,
  loading = false,
  onGenerate,
  onCancel,
  onReset,
  onChapterCreated,
  onChapterSelected,
  status,
  errorMessage,
}: CreationConsoleProps) {
  const [chapterNumber, setChapterNumber] = useState(1)
  const [chapterTitle, setChapterTitle] = useState('')
  const [panelError, setPanelError] = useState('')
  const [creating, setCreating] = useState(false)

  const selectedStoryId = selectedStory?.id || ''
  const selectedChapterId = selectedChapter?.id || ''
  const isRunning = status === 'connecting' || status === 'generating'
  const busy = isRunning || loading || creating
  const selectedWorkflowStage = normalizeStage(
    selectedChapter?.workflowStage ?? selectedChapter?.workflow_stage,
  )
  const draftConfirmed = isDraftConfirmedStage(selectedWorkflowStage)
  const generationUnlocked = isDraftGenerationUnlocked(selectedWorkflowStage)
  const lastChapter = useMemo(() => getLastChapter(chapters), [chapters])
  const nextChapterNumber = useMemo(() => getNextChapterNumber(chapters), [chapters])
  const canContinueToNextChapter =
    chapters.length === 0 || (lastChapter ? isChapterContinuationUnlocked(lastChapter) : false)
  const nextChapterDisabled = busy || !selectedStoryId || !canContinueToNextChapter
  const nextChapterDisabledReason = !selectedStoryId
    ? 'Select a novel first'
    : !canContinueToNextChapter
      ? 'Last chapter must be approved before continuing'
      : undefined

  async function handleCreateChapter(event: FormEvent) {
    event.preventDefault()
    if (!selectedStoryId || chapterNumber < 1) return

    await createChapterForStory(chapterNumber)
  }

  async function handleCreateNextChapter() {
    if (nextChapterDisabled) return
    await createChapterForStory(nextChapterNumber)
  }

  async function createChapterForStory(nextNumber: number) {
    setCreating(true)
    setPanelError('')
    try {
      const chapter = await createChapter(selectedStoryId, {
        chapterNumber: nextNumber,
        title: chapterTitle.trim() || undefined,
      })
      onChapterCreated(chapter)
      setChapterTitle('')
      setChapterNumber(getChapterNumber(chapter) + 1)
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : 'Failed to create chapter')
    } finally {
      setCreating(false)
    }
  }

  function handleGenerate() {
    if (!isRunning && selectedStoryId && selectedChapterId && generationUnlocked && !draftConfirmed) {
      onGenerate(selectedStoryId, selectedChapterId)
    }
  }

  return (
    <div className="creation-console">
      <div className="console-header">
        <div>
          <h2>Chapter Console</h2>
          <p>{selectedStory ? selectedStory.title : 'No novel selected'}</p>
        </div>
        <span>{busy ? 'Working' : 'Ready'}</span>
      </div>

      <form className="console-section" onSubmit={handleCreateChapter}>
        <div className="section-title">Chapter setup</div>
        <button
          type="button"
          className="btn-primary btn-next-chapter"
          onClick={() => void handleCreateNextChapter()}
          disabled={nextChapterDisabled}
          title={nextChapterDisabledReason}
        >
          Next chapter #{nextChapterNumber}
        </button>
        <div className="split-row">
          <label>
            <span>No.</span>
            <input
              type="number"
              min={1}
              value={chapterNumber}
              onChange={(event) => setChapterNumber(Number(event.target.value))}
              disabled={busy || !selectedStoryId}
            />
          </label>
          <label>
            <span>Title</span>
            <input
              type="text"
              value={chapterTitle}
              onChange={(event) => setChapterTitle(event.target.value)}
              placeholder="Chapter title"
              disabled={busy || !selectedStoryId}
            />
          </label>
        </div>
        <button
          type="submit"
          className="btn-secondary"
          disabled={busy || !selectedStoryId}
        >
          Create chapter
        </button>
      </form>

      <div className="console-section">
        <div className="section-title">Selected chapter</div>
        <div className="chapter-list compact" aria-label="Chapter picker">
          {chapters.length === 0 ? (
            <div className="empty-list">No chapters yet</div>
          ) : (
            chapters.map((chapter) => (
              <button
                type="button"
                key={chapter.id}
                className={`chapter-row ${chapter.id === selectedChapterId ? 'selected' : ''}`}
                onClick={() => onChapterSelected(chapter.id)}
                aria-pressed={chapter.id === selectedChapterId}
                disabled={isRunning}
              >
                <span className="chapter-main">
                  <strong>#{getChapterNumber(chapter)}</strong>
                  {chapter.title || 'Untitled'}
                </span>
                <span className="chapter-meta">
                  {chapter.status}
                  {' / '}
                  {formatWorkflowStage(chapter.workflowStage ?? chapter.workflow_stage)}
                  {' / '}
                  {getWordCount(chapter).toLocaleString()} chars
                </span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="generate-bar">
        {!isRunning ? (
          <button
            type="button"
            className="btn-primary"
            onClick={handleGenerate}
            disabled={!selectedStoryId || !selectedChapterId || !generationUnlocked || draftConfirmed}
          >
            {draftConfirmed ? 'Draft confirmed' : 'Generate selected chapter'}
          </button>
        ) : (
          <button type="button" className="btn-danger" onClick={onCancel}>
            Stop
          </button>
        )}

        {status !== 'idle' && !isRunning && (
          <button type="button" className="btn-secondary" onClick={onReset}>
            Reset
          </button>
        )}
      </div>

      {(panelError || errorMessage) && (
        <div className="status-message error">{panelError || errorMessage}</div>
      )}
      {selectedChapter && !generationUnlocked && !draftConfirmed && (
        <div className="status-message">
          Confirm this chapter outline before draft generation.
        </div>
      )}
      {draftConfirmed && (
        <div className="status-message success">
          Draft confirmed. Memory extraction is the next step.
        </div>
      )}
      {status === 'done' && <div className="status-message success">Generation complete</div>}
    </div>
  )
}

function getChapterNumber(chapter: Chapter) {
  return chapter.chapterNumber ?? chapter.chapter_number ?? 0
}

function getNextChapterNumber(chapters: Chapter[]) {
  return Math.max(0, ...chapters.map((chapter) => getChapterNumber(chapter))) + 1
}

function getLastChapter(chapters: Chapter[]) {
  return chapters.reduce<Chapter | null>((latest, chapter) => {
    if (!latest) return chapter
    return getChapterNumber(chapter) > getChapterNumber(latest) ? chapter : latest
  }, null)
}

function getWordCount(chapter: Chapter) {
  return chapter.wordCount ?? chapter.word_count ?? 0
}

function normalizeStage(value?: string) {
  return (value || '').toLowerCase()
}

function isDraftGenerationUnlocked(stage: string) {
  return [
    'outline_confirmed',
    'draft_generating',
    'draft_generated',
    'draft_ready_for_confirmation',
    'reviewing',
    'revision_required',
  ].includes(stage)
}

function isDraftConfirmedStage(stage: string) {
  return [
    'draft_confirmed',
    'memory_extracting',
    'memory_pending_confirmation',
    'memory_confirmed',
    'chapter_confirmed',
  ].includes(stage)
}

function isChapterContinuationUnlocked(chapter: Chapter) {
  const workflowStage = normalizeStage(chapter.workflowStage ?? chapter.workflow_stage)
  const status = normalizeStage(chapter.status)
  return workflowStage === 'chapter_confirmed' || workflowStage === 'approved' || status === 'approved'
}

function formatWorkflowStage(value?: string) {
  if (!value) return 'chapter created'
  return value.replaceAll('_', ' ')
}
