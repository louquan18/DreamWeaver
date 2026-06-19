import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { createChapter, createStory, listChapters, listStories } from '../services/api'
import type { Chapter, Story } from '../types'
import './CreationConsole.css'

interface CreationConsoleProps {
  onGenerate: (storyId: string, chapterId: string) => void
  onCancel: () => void
  onReset: () => void
  onSelectionChange: (story: Story | null, chapter: Chapter | null) => void
  refreshKey: number
  storyRefreshKey?: number
  preferredStoryId?: string
  status: 'idle' | 'connecting' | 'generating' | 'done' | 'error'
  errorMessage: string
}

export function CreationConsole({
  onGenerate,
  onCancel,
  onReset,
  onSelectionChange,
  refreshKey,
  storyRefreshKey = 0,
  preferredStoryId,
  status,
  errorMessage,
}: CreationConsoleProps) {
  const [stories, setStories] = useState<Story[]>([])
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [selectedStoryId, setSelectedStoryId] = useState('')
  const [selectedChapterId, setSelectedChapterId] = useState('')
  const [storyTitle, setStoryTitle] = useState('')
  const [storyGenre, setStoryGenre] = useState('')
  const [storyDescription, setStoryDescription] = useState('')
  const [chapterNumber, setChapterNumber] = useState(1)
  const [chapterTitle, setChapterTitle] = useState('')
  const [panelError, setPanelError] = useState('')
  const [loading, setLoading] = useState(false)

  const isRunning = status === 'connecting' || status === 'generating'

  const selectedStory = useMemo(
    () => stories.find((story) => story.id === selectedStoryId) || null,
    [stories, selectedStoryId],
  )

  const selectedChapter = useMemo(
    () => chapters.find((chapter) => chapter.id === selectedChapterId) || null,
    [chapters, selectedChapterId],
  )

  const selectedWorkflowStage = normalizeStage(
    selectedChapter?.workflowStage ?? selectedChapter?.workflow_stage,
  )
  const draftConfirmed = isDraftConfirmedStage(selectedWorkflowStage)
  const generationUnlocked = isDraftGenerationUnlocked(selectedWorkflowStage)

  const refreshStories = useCallback(async () => {
    try {
      const data = await listStories()
      setStories(data)
      if (preferredStoryId && data.some((story) => story.id === preferredStoryId)) {
        setSelectedStoryId(preferredStoryId)
      } else if (!selectedStoryId && data.length > 0) {
        setSelectedStoryId(data[0].id)
      }
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : 'Failed to load stories')
    } finally {
      setLoading(false)
    }
  }, [preferredStoryId, selectedStoryId])

  const refreshChapters = useCallback(async (storyId: string) => {
    try {
      const data = await listChapters(storyId)
      setChapters(data)
      setSelectedChapterId((current) => {
        if (data.some((chapter) => chapter.id === current)) return current
        return data[0]?.id || ''
      })
      const nextNumber = Math.max(0, ...data.map((chapter) => getChapterNumber(chapter))) + 1
      setChapterNumber(nextNumber)
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : 'Failed to load chapters')
      setChapters([])
      setSelectedChapterId('')
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshStories()
  }, [refreshStories, storyRefreshKey])

  useEffect(() => {
    if (selectedStoryId) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      void refreshChapters(selectedStoryId)
    }
  }, [refreshChapters, refreshKey, selectedStoryId])

  useEffect(() => {
    onSelectionChange(selectedStory, selectedChapter)
  }, [onSelectionChange, selectedStory, selectedChapter])

  async function handleCreateStory(e: FormEvent) {
    e.preventDefault()
    if (!storyTitle.trim()) return

    setLoading(true)
    setPanelError('')
    try {
      const story = await createStory({
        title: storyTitle.trim(),
        genre: storyGenre.trim() || undefined,
        description: storyDescription.trim() || undefined,
      })
      setStories((prev) => [story, ...prev])
      setSelectedStoryId(story.id)
      setStoryTitle('')
      setStoryGenre('')
      setStoryDescription('')
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : 'Failed to create story')
    } finally {
      setLoading(false)
    }
  }

  async function handleCreateChapter(e: FormEvent) {
    e.preventDefault()
    if (!selectedStoryId || chapterNumber < 1) return

    setLoading(true)
    setPanelError('')
    try {
      const chapter = await createChapter(selectedStoryId, {
        chapterNumber,
        title: chapterTitle.trim() || undefined,
      })
      setChapters((prev) => [...prev, chapter].sort(compareChapters))
      setSelectedChapterId(chapter.id)
      setChapterTitle('')
      setChapterNumber((prev) => prev + 1)
    } catch (error) {
      setPanelError(error instanceof Error ? error.message : 'Failed to create chapter')
    } finally {
      setLoading(false)
    }
  }

  function handleGenerate() {
    if (!isRunning && selectedStoryId && selectedChapterId && generationUnlocked && !draftConfirmed) {
      onGenerate(selectedStoryId, selectedChapterId)
    }
  }

  function handleStorySelect(storyId: string) {
    setPanelError('')
    setSelectedStoryId(storyId)
    setChapters([])
    setSelectedChapterId('')
  }

  function handleChapterSelect(chapterId: string) {
    setPanelError('')
    setSelectedChapterId(chapterId)
  }

  return (
    <div className="creation-console">
      <div className="console-header">
        <h2>Creation Console</h2>
        <span>{loading ? 'Syncing' : 'Ready'}</span>
      </div>

      <form className="console-section" onSubmit={handleCreateStory}>
        <div className="section-title">Novel</div>
        <label>
          <span>Create novel</span>
          <input
            type="text"
            value={storyTitle}
            onChange={(e) => setStoryTitle(e.target.value)}
            placeholder="Title"
            disabled={isRunning || loading}
          />
        </label>
        <div className="split-row">
          <input
            type="text"
            value={storyGenre}
            onChange={(e) => setStoryGenre(e.target.value)}
            placeholder="Genre"
            disabled={isRunning || loading}
          />
          <button type="submit" disabled={isRunning || loading || !storyTitle.trim()}>
            Create
          </button>
        </div>
        <textarea
          value={storyDescription}
          onChange={(e) => setStoryDescription(e.target.value)}
          placeholder="Brief description"
          disabled={isRunning || loading}
          rows={3}
        />

        <label>
          <span>Select novel</span>
          <select
            value={selectedStoryId}
            onChange={(e) => handleStorySelect(e.target.value)}
            disabled={isRunning || loading || stories.length === 0}
          >
            <option value="">No novel selected</option>
            {stories.map((story) => (
              <option key={story.id} value={story.id}>
                {story.title}
              </option>
            ))}
          </select>
        </label>
      </form>

      <form className="console-section" onSubmit={handleCreateChapter}>
        <div className="section-title">Chapter</div>
        <div className="split-row">
          <label>
            <span>No.</span>
            <input
              type="number"
              min={1}
              value={chapterNumber}
              onChange={(e) => setChapterNumber(Number(e.target.value))}
              disabled={isRunning || loading || !selectedStoryId}
            />
          </label>
          <label>
            <span>Title</span>
            <input
              type="text"
              value={chapterTitle}
              onChange={(e) => setChapterTitle(e.target.value)}
              placeholder="Chapter title"
              disabled={isRunning || loading || !selectedStoryId}
            />
          </label>
        </div>
        <button type="submit" disabled={isRunning || loading || !selectedStoryId}>
          Create chapter
        </button>

        <div className="chapter-list" aria-label="Chapter list">
          {chapters.length === 0 ? (
            <div className="empty-list">No chapters yet</div>
          ) : (
            chapters.map((chapter) => (
              <button
                type="button"
                key={chapter.id}
                className={`chapter-row ${chapter.id === selectedChapterId ? 'selected' : ''}`}
                onClick={() => handleChapterSelect(chapter.id)}
                aria-pressed={chapter.id === selectedChapterId}
              >
                <span className="chapter-main">
                  <strong>#{getChapterNumber(chapter)}</strong>
                  {chapter.title || 'Untitled'}
                </span>
                <span className="chapter-meta">
                  {chapter.status}
                  {' · '}
                  {formatWorkflowStage(chapter.workflowStage ?? chapter.workflow_stage)}
                  {' · '}
                  {getWordCount(chapter).toLocaleString()} chars
                  {' · '}
                  {chapter.content ? 'has text' : 'empty'}
                </span>
              </button>
            ))
          )}
        </div>
      </form>

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

function compareChapters(a: Chapter, b: Chapter) {
  return getChapterNumber(a) - getChapterNumber(b)
}

function getChapterNumber(chapter: Chapter) {
  return chapter.chapterNumber ?? chapter.chapter_number ?? 0
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

function formatWorkflowStage(value?: string) {
  if (!value) return 'chapter created'
  return value.replaceAll('_', ' ')
}
