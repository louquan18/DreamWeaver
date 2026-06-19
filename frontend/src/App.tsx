import { useCallback, useState } from 'react'
import { CreationConsole } from './components/CreationConsole'
import { LivePreview } from './components/LivePreview'
import { AgentStatus } from './components/AgentStatus'
import { GenerationHistory } from './components/GenerationHistory'
import { NovelIdeaChat } from './components/NovelIdeaChat'
import { useSSE } from './hooks/useSSE'
import type { Chapter, Story } from './types'
import './App.css'

function App() {
  const { state, startGeneration, cancel, reset } = useSSE()
  const [selectedStory, setSelectedStory] = useState<Story | null>(null)
  const [selectedChapter, setSelectedChapter] = useState<Chapter | null>(null)
  const [historyPreview, setHistoryPreview] = useState('')
  const [chapterRefreshKey, setChapterRefreshKey] = useState(0)
  const [storyRefreshKey, setStoryRefreshKey] = useState(0)
  const [preferredStoryId, setPreferredStoryId] = useState<string | undefined>()

  const handleGenerate = useCallback((storyId: string, chapterId: string) => {
    setHistoryPreview('')
    startGeneration({ story_id: storyId, chapter_id: chapterId })
  }, [startGeneration])

  const handleSelectionChange = useCallback((story: Story | null, chapter: Chapter | null) => {
    setSelectedStory(story)
    setSelectedChapter(chapter)
    setHistoryPreview('')
  }, [])

  const handleChapterUpdated = useCallback((chapter: Chapter) => {
    setSelectedChapter(chapter)
    setHistoryPreview('')
    setChapterRefreshKey((value) => value + 1)
  }, [])

  const handleStoryCreated = useCallback((story: Story) => {
    setSelectedStory(story)
    setSelectedChapter(null)
    setPreferredStoryId(story.id)
    setStoryRefreshKey((value) => value + 1)
  }, [])

  const isGenerating = state.status === 'generating' || state.status === 'connecting'
  const previewText = isGenerating ? state.draft : historyPreview || selectedChapter?.content || ''

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
        <div className="left-panel">
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
          <AgentStatus
            currentNode={state.currentNode}
            executionHistory={state.executionHistory}
            progress={state.progress}
          />
          <GenerationHistory
            storyId={selectedStory?.id}
            chapterId={selectedChapter?.id}
            refreshKey={state.completionSeq}
            onPreview={setHistoryPreview}
            onAdopted={handleChapterUpdated}
          />
        </div>

        <div className="right-panel">
          <LivePreview
            draft={previewText}
            isGenerating={isGenerating}
          />
        </div>
      </main>
    </div>
  )
}

export default App
