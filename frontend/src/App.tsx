// DreamWeaver 前端主应用

import { CreationConsole } from './components/CreationConsole'
import { LivePreview } from './components/LivePreview'
import { AgentStatus } from './components/AgentStatus'
import { useSSE } from './hooks/useSSE'
import './App.css'

function App() {
  const { state, startGeneration, cancel, reset } = useSSE()

  const handleGenerate = (storyId: string, chapterId: string) => {
    startGeneration({ story_id: storyId, chapter_id: chapterId })
  }

  return (
    <div className="app">
      <header className="app-header">
        <h1>🌌 DreamWeaver</h1>
        <span className="app-subtitle">织梦者 · Multi-Agent 长篇小说创作系统</span>
      </header>

      <main className="app-main">
        <div className="left-panel">
          <CreationConsole
            onGenerate={handleGenerate}
            onCancel={cancel}
            onReset={reset}
            status={state.status}
            errorMessage={state.errorMessage}
          />
          <AgentStatus
            currentNode={state.currentNode}
            executionHistory={state.executionHistory}
            progress={state.progress}
          />
        </div>

        <div className="right-panel">
          <LivePreview
            draft={state.draft}
            isGenerating={state.status === 'generating' || state.status === 'connecting'}
          />
        </div>
      </main>
    </div>
  )
}

export default App
