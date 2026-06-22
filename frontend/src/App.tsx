import { useCallback, useState } from 'react'
import { CreationConsole } from './components/CreationConsole'
import { LivePreview } from './components/LivePreview'
import { AgentStatus } from './components/AgentStatus'
import { GenerationHistory } from './components/GenerationHistory'
import { MemoryChangeSetPanel } from './components/MemoryChangeSetPanel'
import { NovelIdeaChat } from './components/NovelIdeaChat'
import { OutlineOptionsPanel } from './components/OutlineOptionsPanel'
import { useSSE } from './hooks/useSSE'
import { confirmChapterGeneration } from './services/api'
import type { Chapter, ChapterGeneration, Story } from './types'
import './App.css'

function App() {
  const { state, startGeneration, cancel, reset } = useSSE()
  const [selectedStory, setSelectedStory] = useState<Story | null>(null)
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null)
  const [selectedGeneration, setSelectedGeneration] = useState<ChapterGeneration | null>(null)
  const [chapterRefreshKey, setChapterRefreshKey] = useState(0)
  const [storyRefreshKey, setStoryRefreshKey] = useState(0)
  const [preferredStoryId, setPreferredStoryId] = useState<string | undefined>()
  const [draftConfirming, setDraftConfirming] = useState(false)
  const [draftConfirmError, setDraftConfirmError] = useState('')

  const handleGenerate = useCallback((storyId: string, chapterId: string) => {
    setSelectedGeneration(null)
    setDraftConfirmError('')
    startGeneration({ story_id: storyId, chapter_id: chapterId })
  }, [startGeneration])

  const handleSelectionChange = useCallback((story: Story | null, chapter: Chapter | null) => {
    setSelectedStory(story)
    setSelectedChapter(chapter)
    setSelectedGeneration(null)
    setDraftConfirmError('')
  }, [])

  const handleChapterUpdated = useCallback((chapter: Chapter) => {
    setSelectedChapter(chapter)
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
      setSelectedChapter(chapter)
      setSelectedGeneration((current) => (
        current?.id === generationId ? { ...current, adopted: true } : current
      ))
      setChapterRefreshKey((value) => value + 1)
    } catch (error) {
      setDraftConfirmError(error instanceof Error ? error.message : 'Failed to confirm draft')
    } finally {
      setDraftConfirming(false)
    }
  }, [draftConfirming, selectedChapter, selectedStory])

  const handleStoryCreated = useCallback((story: Story) => {
    setSelectedStory(story)
    setSelectedChapter(null)
    setPreferredStoryId(story.id)
    setStoryRefreshKey((value) => value + 1)
  }, [])

  const isGenerating = state.status === 'generating' || state.status === 'connecting'
  const previewText = isGenerating ? state.draft : selectedGeneration?.draft || selectedChapter?.content || ''

  return (
    <div className="app">
      <header className="app-header">
        <h1>DreamWeaver</h1>
        <span className="app-subtitle">
          {selectedStory ? selectedStory.title : 'Select or create a novel'}
          {selectedChapter
            ? ` / #${selectedChapter.chapterNumber ?? selectedChapter.chapter_number ?? 0} ${selectedChapter.title || ''}`
            : ''}
        </span>
      </header>

      <main className="app-main">
        <aside className="workspace-sidebar" aria-label="Blueprint and chapter navigation">
          <NovelIdeaChat onStoryCreated={handleStoryCreated} />
          <CreationConsole
            onGenerate={handleGenerate}
            onCancel={cancel}
            onReset={reset}
            onSelectionChange={handleSelectionChange}
            refreshKey={chapterRefreshKey + state.completionSeq}
            storyRefreshKey={storyRefreshKey}
            preferredStoryId={preferredStoryId}
            status={state.status}
            errorMessage={state.errorMessage}
          />
        </aside>

        <section className="workspace-editor" aria-label="Chapter draft workspace">
          <LivePreview
            draft={previewText}
            isGenerating={isGenerating}
            status={state.status}
            errorMessage={draftConfirmError || state.errorMessage}
            generationId={state.generationId}
            generation={selectedGeneration}
            chapter={selectedChapter}
            runtimeHistory={state.executionHistory}
            confirming={draftConfirming}
            onConfirmDraft={handleConfirmDraft}
          />
        </section>

        <aside className="workspace-rail" aria-label="Agent workflow assistance">
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
          <GenerationHistory
            storyId={selectedStory?.id}
            chapterId={selectedChapter?.id}
            refreshKey={state.completionSeq + chapterRefreshKey}
            onGenerationSelected={handleGenerationSelected}
            onConfirmed={handleChapterUpdated}
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
        </aside>
      </main>
    </div>
  )
}

export default App
