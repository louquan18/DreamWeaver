// 实时预览组件 - SSE 流式显示章节内容

import './LivePreview.css'

interface LivePreviewProps {
  draft: string
  isGenerating: boolean
}

export function LivePreview({ draft, isGenerating }: LivePreviewProps) {
  const wordCount = draft.length

  return (
    <div className="live-preview">
      <div className="preview-header">
        <h3>📝 章节预览</h3>
        <div className="preview-meta">
          <span className="word-count">{wordCount.toLocaleString()} 字</span>
          {isGenerating && <span className="typing-indicator">生成中...</span>}
        </div>
      </div>

      <div className="preview-content">
        {draft ? (
          <div className="draft-text">
            {draft.split('\n').map((line, i) => (
              <p key={i}>{line || <br />}</p>
            ))}
            {isGenerating && <span className="cursor-blink">|</span>}
          </div>
        ) : (
          <div className="empty-state">
            <p>📋 点击「开始生成」创建章节</p>
            <p className="hint">AI 将自动规划、写作、检查和评审</p>
          </div>
        )}
      </div>
    </div>
  )
}
