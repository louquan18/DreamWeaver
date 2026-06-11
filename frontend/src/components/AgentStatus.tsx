// Agent 状态监控面板

import './AgentStatus.css'

interface AgentStatusProps {
  currentNode: string
  executionHistory: string[]
  progress: number
}

const NODE_LABELS: Record<string, string> = {
  load_runtime_context: '加载上下文',
  novel_context: '构建记忆',
  plan_chapter: '规划章节',
  generate_draft: '生成草稿',
  check_consistency: '一致性检查',
  review: '质量评审',
  rewrite: '重写优化',
  commit: '提交完成',
}

const ALL_NODES = [
  'load_runtime_context',
  'novel_context',
  'plan_chapter',
  'generate_draft',
  'check_consistency',
  'review',
  'commit',
]

export function AgentStatus({ currentNode, executionHistory, progress }: AgentStatusProps) {
  const getNodeStatus = (node: string) => {
    if (executionHistory.includes(node)) return 'completed'
    if (node === currentNode) return 'active'
    return 'pending'
  }

  return (
    <div className="agent-status">
      <h3>🔄 工作流进度</h3>

      <div className="progress-bar">
        <div className="progress-fill" style={{ width: `${progress}%` }} />
        <span className="progress-text">{progress}%</span>
      </div>

      <div className="node-list">
        {ALL_NODES.map((node) => {
          const status = getNodeStatus(node)
          return (
            <div key={node} className={`node-item ${status}`}>
              <span className="node-icon">
                {status === 'completed' ? '✅' : status === 'active' ? '⚡' : '⏳'}
              </span>
              <span className="node-label">{NODE_LABELS[node] || node}</span>
              {status === 'active' && <span className="node-spinner" />}
            </div>
          )
        })}
      </div>

      {executionHistory.includes('rewrite') && (
        <div className="rewrite-badge">
          🔄 已重写 {executionHistory.filter((n) => n === 'rewrite').length} 次
        </div>
      )}
    </div>
  )
}
