import { useCallback, useEffect, useMemo, useState } from 'react'
import { AgentStatus } from './components/AgentStatus'
import { CreationConsole } from './components/CreationConsole'
import { CreateStoryDialog, type CreateStoryIntent } from './components/CreateStoryDialog'
import { GenerationHistory } from './components/GenerationHistory'
import { LivePreview } from './components/LivePreview'
import { MemoryChangeSetPanel } from './components/MemoryChangeSetPanel'
import { MemoryLibraryView } from './components/MemoryLibraryView'
import { NovelIdeaChat } from './components/NovelIdeaChat'
import { OutlineOptionsPanel } from './components/OutlineOptionsPanel'
import { StoryWorkspaceSidebar } from './components/StoryWorkspaceSidebar'
import { WorkspaceActionRail } from './components/WorkspaceActionRail'
import { WorkspaceMain } from './components/WorkspaceMain'
import { WorkspaceShell } from './components/WorkspaceShell'
import { getWorkspaceNavItem, type WorkspaceView } from './components/workspaceTypes'
import { useSSE } from './hooks/useSSE'
import {
  confirmChapterGeneration,
  createStory,
  getChapterGeneration,
  listChapters,
  listChapterGenerations,
  listStories,
} from './services/api'
import type { Chapter, ChapterGeneration, Story } from './types'
import './App.css'

function App() {
  const { state, startGeneration, cancel, reset } = useSSE()
  const [stories, setStories] = useState<Story[]>([])
  const [chapters, setChapters] = useState<Chapter[]>([])
  const [selectedStoryId, setSelectedStoryId] = useState('')
  const [selectedChapterId, setSelectedChapterId] = useState('')
  const [selectedGeneration, setSelectedGeneration] = useState<ChapterGeneration | null>(null)
  const [activeView, setActiveView] = useState<WorkspaceView>('chapters')
  const [loadingStories, setLoadingStories] = useState(false)
  const [loadingChapters, setLoadingChapters] = useState(false)
  const [selectionError, setSelectionError] = useState('')
  const [createDialogOpen, setCreateDialogOpen] = useState(false)
  const [creatingStory, setCreatingStory] = useState(false)
  const [createStoryError, setCreateStoryError] = useState('')
  const [autoBlueprint, setAutoBlueprint] = useState<{ storyId: string; prompt: string; key: number } | null>(null)
  const [chapterRefreshKey, setChapterRefreshKey] = useState(0)
  const [draftConfirming, setDraftConfirming] = useState(false)
  const [draftConfirmError, setDraftConfirmError] = useState('')

  const selectedStory = useMemo(
    () => stories.find((story) => story.id === selectedStoryId) || null,
    [selectedStoryId, stories],
  )
  const selectedChapter = useMemo(
    () => chapters.find((chapter) => chapter.id === selectedChapterId) || null,
    [chapters, selectedChapterId],
  )
  const isGenerating = state.status === 'generating' || state.status === 'connecting'
  const activeGeneration = mergeActiveGeneration(selectedGeneration, state.generation)
  const previewText = isGenerating ? state.draft : activeGeneration?.draft || selectedChapter?.content || ''

  const refreshStories = useCallback(async () => {
    setLoadingStories(true)
    setSelectionError('')
    try {
      const data = await listStories()
      setStories(data)
      setSelectedStoryId((current) => {
        if (current && data.some((story) => story.id === current)) return current
        return data[0]?.id || ''
      })
    } catch (error) {
      setSelectionError(error instanceof Error ? error.message : 'Failed to load novels')
    } finally {
      setLoadingStories(false)
    }
  }, [])

  const refreshChapters = useCallback(async (storyId: string) => {
    if (!storyId) {
      setChapters([])
      setSelectedChapterId('')
      return
    }

    setLoadingChapters(true)
    setSelectionError('')
    try {
      const data = await listChapters(storyId)
      setChapters(data)
      setSelectedChapterId((current) => {
        if (current && data.some((chapter) => chapter.id === current)) return current
        return data[0]?.id || ''
      })
    } catch (error) {
      setChapters([])
      setSelectedChapterId('')
      setSelectionError(error instanceof Error ? error.message : 'Failed to load chapters')
    } finally {
      setLoadingChapters(false)
    }
  }, [])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void refreshStories()
  }, [refreshStories])

  useEffect(() => {
    /* eslint-disable react-hooks/set-state-in-effect */
    setSelectedGeneration(null)
    setDraftConfirmError('')
    void refreshChapters(selectedStoryId)
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [refreshChapters, selectedStoryId, chapterRefreshKey])

  useEffect(() => {
    if (!selectedStoryId || !selectedChapterId) {
      return
    }
    if (isGenerating) return
    if (state.generation?.chapterId === selectedChapterId) return

    let cancelled = false
    async function loadLatestGenerationDetail() {
      try {
        const generations = await listChapterGenerations(selectedStoryId, selectedChapterId)
        const latest = generations.find((item) => item.status === 'succeeded') || generations[0]
        if (!latest) {
          if (!cancelled) setSelectedGeneration(null)
          return
        }
        const detail = await getChapterGeneration(selectedStoryId, selectedChapterId, latest.id)
        if (!cancelled) setSelectedGeneration(detail)
      } catch {
        if (!cancelled) setSelectedGeneration(null)
      }
    }

    void loadLatestGenerationDetail()
    return () => {
      cancelled = true
    }
  }, [isGenerating, selectedChapterId, selectedStoryId, state.generation?.chapterId])

  const handleGenerate = useCallback((storyId: string, chapterId: string) => {
    setSelectedGeneration(null)
    setDraftConfirmError('')
    startGeneration({ story_id: storyId, chapter_id: chapterId })
  }, [startGeneration])

  const handleCreateStory = useCallback(async (input: {
    title: string
    genre?: string
    description?: string
  }, intent: CreateStoryIntent = 'create') => {
    setCreatingStory(true)
    setCreateStoryError('')
    try {
      const story = await createStory(input)
      reset()
      setStories((current) => [story, ...current.filter((item) => item.id !== story.id)])
      setSelectedStoryId(story.id)
      setSelectedChapterId('')
      setSelectedGeneration(null)
      setDraftConfirmError('')
      setActiveView('blueprint')
      setCreateDialogOpen(false)
      if (intent === 'blueprint') {
        setAutoBlueprint({
          storyId: story.id,
          prompt: input.description?.trim() || input.title,
          key: Date.now(),
        })
      }
    } catch (error) {
      setCreateStoryError(error instanceof Error ? error.message : 'Failed to create novel')
      throw error
    } finally {
      setCreatingStory(false)
    }
  }, [reset])

  const handleStoryCreatedFromBlueprint = useCallback((story: Story) => {
    reset()
    setStories((current) => [story, ...current.filter((item) => item.id !== story.id)])
    setSelectedStoryId(story.id)
    setSelectedChapterId('')
    setSelectedGeneration(null)
    setDraftConfirmError('')
    setActiveView('blueprint')
  }, [reset])

  const handleStorySelect = useCallback((storyId: string) => {
    if (storyId !== selectedStoryId) {
      reset()
    }
    setSelectedStoryId(storyId)
    setSelectedChapterId('')
    setSelectedGeneration(null)
    setDraftConfirmError('')
  }, [reset, selectedStoryId])

  const handleChapterSelected = useCallback((chapterId: string) => {
    if (chapterId !== selectedChapterId) {
      reset()
    }
    setSelectedChapterId(chapterId)
    setSelectedGeneration(null)
    setDraftConfirmError('')
    if (activeView === 'blueprint') {
      setActiveView('chapters')
    }
  }, [activeView, reset, selectedChapterId])

  const handleChapterUpdated = useCallback((chapter: Chapter) => {
    setSelectedChapterId(chapter.id)
    setChapters((current) => upsertChapter(current, chapter))
    setChapterRefreshKey((value) => value + 1)
  }, [])

  const handleGenerationSelected = useCallback((generation: ChapterGeneration | null) => {
    setSelectedGeneration(generation)
    setDraftConfirmError('')
  }, [])

  const handleConfirmDraft = useCallback(async (generationId: string) => {
    if (!selectedStory?.id || !selectedChapter?.id || draftConfirming) return

    setDraftConfirming(true)
    setDraftConfirmError('')
    try {
      const chapter = await confirmChapterGeneration(selectedStory.id, selectedChapter.id, generationId)
      handleChapterUpdated(chapter)
      setSelectedGeneration((current) => (
        current?.id === generationId ? { ...current, adopted: true } : current
      ))
    } catch (error) {
      setDraftConfirmError(error instanceof Error ? error.message : 'Failed to confirm draft')
    } finally {
      setDraftConfirming(false)
    }
  }, [draftConfirming, handleChapterUpdated, selectedChapter, selectedStory])

  return (
    <div className="app">
      <header className="app-header">
        <div>
          <span className="app-kicker">DreamWeaver</span>
          <h1>{selectedStory ? selectedStory.title : 'Novel Workspace'}</h1>
        </div>
        <p className="app-subtitle">
          {selectedChapter
            ? `#${selectedChapter.chapterNumber ?? selectedChapter.chapter_number ?? 0} ${selectedChapter.title || 'Untitled'}`
            : getWorkspaceNavItem(activeView).detail}
        </p>
      </header>

      <WorkspaceShell
        sidebar={(
          <StoryWorkspaceSidebar
            stories={stories}
            chapters={chapters}
            selectedStoryId={selectedStoryId}
            selectedChapterId={selectedChapterId}
            activeView={activeView}
            loadingStories={loadingStories}
            loadingChapters={loadingChapters}
            selectionError={selectionError}
            isRunning={isGenerating}
            onOpenCreateStory={() => {
              setCreateStoryError('')
              setCreateDialogOpen(true)
            }}
            onRefreshStories={refreshStories}
            onSelectStory={handleStorySelect}
            onSelectChapter={handleChapterSelected}
            onSelectView={setActiveView}
          />
        )}
        main={(
          <WorkspaceMain activeView={activeView} story={selectedStory} chapter={selectedChapter}>
            {renderMainView({
              activeGeneration,
              activeView,
              autoBlueprint,
              draftConfirmError,
              draftConfirming,
              handleChapterUpdated,
              handleConfirmDraft,
              handleGenerationSelected,
              handleStoryCreatedFromBlueprint,
              isGenerating,
              onCreateStoryClick: () => {
                setCreateStoryError('')
                setCreateDialogOpen(true)
              },
              previewText,
              selectedChapter,
              selectedStory,
              state,
            })}
          </WorkspaceMain>
        )}
        actionRail={(
          <WorkspaceActionRail activeView={activeView}>
            {renderActionView({
              activeView,
              cancel,
              chapterRefreshKey,
              chapters,
              handleChapterSelected,
              handleChapterUpdated,
              handleGenerate,
              handleGenerationSelected,
              reset,
              selectedChapter,
              selectedStory,
              state,
            })}
          </WorkspaceActionRail>
        )}
      />

      <CreateStoryDialog
        open={createDialogOpen}
        creating={creatingStory}
        error={createStoryError}
        onClose={() => {
          if (!creatingStory) setCreateDialogOpen(false)
        }}
        onCreate={handleCreateStory}
      />
    </div>
  )
}

function renderMainView({
  activeGeneration,
  activeView,
  autoBlueprint,
  draftConfirmError,
  draftConfirming,
  handleChapterUpdated,
  handleConfirmDraft,
  handleGenerationSelected,
  handleStoryCreatedFromBlueprint,
  isGenerating,
  onCreateStoryClick,
  previewText,
  selectedChapter,
  selectedStory,
  state,
}: {
  activeGeneration: ChapterGeneration | null
  activeView: WorkspaceView
  autoBlueprint: { storyId: string; prompt: string; key: number } | null
  draftConfirmError: string
  draftConfirming: boolean
  handleChapterUpdated: (chapter: Chapter) => void
  handleConfirmDraft: (generationId: string) => void
  handleGenerationSelected: (generation: ChapterGeneration | null) => void
  handleStoryCreatedFromBlueprint: (story: Story) => void
  isGenerating: boolean
  onCreateStoryClick: () => void
  previewText: string
  selectedChapter: Chapter | null
  selectedStory: Story | null
  state: ReturnType<typeof useSSE>['state']
}) {
  if (activeView === 'blueprint') {
    const blueprintSeed = autoBlueprint && autoBlueprint.storyId === selectedStory?.id ? autoBlueprint : null
    return (
      <NovelIdeaChat
        story={selectedStory}
        autoGeneratePrompt={blueprintSeed?.prompt}
        autoGenerateKey={blueprintSeed?.key}
        onCreateStoryClick={onCreateStoryClick}
        onStoryCreated={handleStoryCreatedFromBlueprint}
      />
    )
  }

  if (activeView === 'history') {
    return (
      <GenerationHistory
        storyId={selectedStory?.id}
        chapterId={selectedChapter?.id}
        refreshKey={state.completionSeq}
        autoSelectGenerationId={state.status === 'done' ? state.generationId : undefined}
        onGenerationSelected={handleGenerationSelected}
        onConfirmed={handleChapterUpdated}
      />
    )
  }

  if (activeView === 'agents') {
    return <AgentStatusPanel state={state} />
  }

  const navItem = getWorkspaceNavItem(activeView)
  if (navItem.memoryType) {
    return <MemoryLibraryView story={selectedStory} type={navItem.memoryType} />
  }

  return (
    <LivePreview
      draft={previewText}
      isGenerating={isGenerating}
      status={state.status}
      errorMessage={draftConfirmError || state.errorMessage}
      generationId={state.generationId}
      generation={activeGeneration}
      chapter={selectedChapter}
      runtimeHistory={state.executionHistory}
      confirming={draftConfirming}
      onConfirmDraft={handleConfirmDraft}
    />
  )
}

function renderActionView({
  activeView,
  cancel,
  chapterRefreshKey,
  chapters,
  handleChapterSelected,
  handleChapterUpdated,
  handleGenerate,
  handleGenerationSelected,
  reset,
  selectedChapter,
  selectedStory,
  state,
}: {
  activeView: WorkspaceView
  cancel: () => void
  chapterRefreshKey: number
  chapters: Chapter[]
  handleChapterSelected: (chapterId: string) => void
  handleChapterUpdated: (chapter: Chapter) => void
  handleGenerate: (storyId: string, chapterId: string) => void
  handleGenerationSelected: (generation: ChapterGeneration | null) => void
  reset: () => void
  selectedChapter: Chapter | null
  selectedStory: Story | null
  state: ReturnType<typeof useSSE>['state']
}) {
  if (activeView === 'chapters') {
    return (
      <>
        <CreationConsole
          selectedStory={selectedStory}
          selectedChapter={selectedChapter}
          chapters={chapters}
          onGenerate={handleGenerate}
          onCancel={cancel}
          onReset={reset}
          onChapterCreated={handleChapterUpdated}
          onChapterSelected={handleChapterSelected}
          status={state.status}
          errorMessage={state.errorMessage}
        />
        <OutlineOptionsPanel
          storyId={selectedStory?.id}
          chapterId={selectedChapter?.id}
          chapter={selectedChapter ?? undefined}
          refreshKey={chapterRefreshKey}
          onChapterConfirmed={handleChapterUpdated}
        />
        <MemoryChangeSetPanel
          storyId={selectedStory?.id}
          chapterId={selectedChapter?.id}
          chapter={selectedChapter}
          refreshKey={chapterRefreshKey}
          onChapterUpdated={handleChapterUpdated}
        />
      </>
    )
  }

  if (activeView === 'history') {
    return <AgentStatusPanel state={state} />
  }

  if (activeView === 'agents') {
    return (
      <GenerationHistory
        storyId={selectedStory?.id}
        chapterId={selectedChapter?.id}
        refreshKey={state.completionSeq + chapterRefreshKey}
        autoSelectGenerationId={state.status === 'done' ? state.generationId : undefined}
        onGenerationSelected={handleGenerationSelected}
        onConfirmed={handleChapterUpdated}
      />
    )
  }

  if (activeView === 'blueprint') {
    return (
      <div className="workspace-note">
        Blueprint creation and confirmation live in the center workspace. Select a chapter to plan
        A/B/C routes after the novel blueprint is confirmed.
      </div>
    )
  }

  return (
    <>
      <div className="workspace-note">
        This library reads the confirmed story memory snapshot. Confirm chapter memory changes to
        promote staged facts into the novel-level library.
      </div>
      <MemoryChangeSetPanel
        storyId={selectedStory?.id}
        chapterId={selectedChapter?.id}
        chapter={selectedChapter}
        refreshKey={chapterRefreshKey}
        onChapterUpdated={handleChapterUpdated}
      />
    </>
  )
}

function AgentStatusPanel({ state }: { state: ReturnType<typeof useSSE>['state'] }) {
  return (
    <AgentStatus
      currentNode={state.currentNode}
      executionHistory={state.executionHistory}
      progress={state.progress}
      status={state.status}
      generationId={state.generationId}
      draftLength={state.draft.length}
      tokenEventCount={state.tokenEventCount}
      tokenCharCount={state.tokenCharCount}
      tokenPreview={state.tokenPreview}
      errorMessage={state.errorMessage}
      agentEvents={state.agentEvents}
    />
  )
}

function upsertChapter(chapters: Chapter[], chapter: Chapter) {
  const exists = chapters.some((item) => item.id === chapter.id)
  const next = exists
    ? chapters.map((item) => item.id === chapter.id ? chapter : item)
    : [...chapters, chapter]
  return next.sort((left, right) => (
    (left.chapterNumber ?? left.chapter_number ?? 0) - (right.chapterNumber ?? right.chapter_number ?? 0)
  ))
}

function mergeActiveGeneration(
  selectedGeneration: ChapterGeneration | null,
  streamedGeneration: ChapterGeneration | null,
) {
  if (!selectedGeneration) return streamedGeneration
  if (!streamedGeneration) return selectedGeneration
  if (selectedGeneration.id !== streamedGeneration.id) return selectedGeneration

  return {
    ...streamedGeneration,
    ...selectedGeneration,
    consistencyReport:
      selectedGeneration.consistencyReport
      || selectedGeneration.consistency_report
      || streamedGeneration.consistencyReport
      || streamedGeneration.consistency_report,
    consistency_report:
      selectedGeneration.consistency_report
      || selectedGeneration.consistencyReport
      || streamedGeneration.consistency_report
      || streamedGeneration.consistencyReport,
    reviewReport:
      selectedGeneration.reviewReport
      || selectedGeneration.review_report
      || streamedGeneration.reviewReport
      || streamedGeneration.review_report,
    review_report:
      selectedGeneration.review_report
      || selectedGeneration.reviewReport
      || streamedGeneration.review_report
      || streamedGeneration.reviewReport,
  }
}

export default App
