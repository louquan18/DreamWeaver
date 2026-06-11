// 创作控制台 - 输入小说 ID 和章节 ID，启动生成

import { useState } from 'react'
import './CreationConsole.css'

interface CreationConsoleProps {
  onGenerate: (storyId: string, chapterId: string) => void
  onCancel: () => void
  onReset: () => void
  status: 'idle' | 'connecting' | 'generating' | 'done' | 'error'
  errorMessage: string
}

export function CreationConsole({
  onGenerate,
  onCancel,
  onReset,
  status,
  errorMessage,
}: CreationConsoleProps) {
  const [storyId, setStoryId] = useState('demo-story')
  const [chapterId, setChapterId] = useState('chapter-1')

  const isRunning = status === 'connecting' || status === 'generating'

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!isRunning && storyId && chapterId) {
      onGenerate(storyId, chapterId)
    }
  }

  return (
    <div className="creation-console">
      <h2>🌌 DreamWeaver 创作控制台</h2>
      <p className="subtitle">Multi-Agent 长篇小说创作系统</p>

      <form onSubmit={handleSubmit}>
        <div className="form-row">
          <label>
            <span>📚 小说 ID</span>
            <input
              type="text"
              value={storyId}
              onChange={(e) => setStoryId(e.target.value)}
              placeholder="story-001"
              disabled={isRunning}
            />
          </label>
          <label>
            <span>📖 章节 ID</span>
            <input
              type="text"
              value={chapterId}
              onChange={(e) => setChapterId(e.target.value)}
              placeholder="chapter-1"
              disabled={isRunning}
            />
          </label>
        </div>

        <div className="button-group">
          {!isRunning ? (
            <button type="submit" className="btn-primary">
              🚀 开始生成
            </button>
          ) : (
            <button type="button" className="btn-danger" onClick={onCancel}>
              ⏹ 停止
            </button>
          )}

          {status !== 'idle' && !isRunning && (
            <button type="button" className="btn-secondary" onClick={onReset}>
              🔄 重置
            </button>
          )}
        </div>
      </form>

      {status === 'done' && (
        <div className="status-message success">✅ 章节生成完成！</div>
      )}

      {status === 'error' && (
        <div className="status-message error">❌ {errorMessage}</div>
      )}
    </div>
  )
}
