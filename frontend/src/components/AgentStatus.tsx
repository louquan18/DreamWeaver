import type { AgentEvent, WorkflowStatus } from '../hooks/useSSE'
import './AgentStatus.css'

interface AgentStatusProps {
  currentNode: string
  executionHistory: string[]
  progress: number
  status?: WorkflowStatus
  generationId?: string
  draftLength?: number
  tokenEventCount?: number
  tokenCharCount?: number
  tokenPreview?: string
  errorMessage?: string
  agentEvents?: AgentEvent[]
}

const NODE_LABELS: Record<string, string> = {
  load_runtime_context: 'Runtime context',
  novel_context: 'Novel memory',
  plan_chapter: 'Chapter plan',
  generate_draft: 'Draft',
  check_consistency: 'Consistency',
  review: 'Review',
  rewrite: 'Rewrite',
  commit: 'Commit',
}

const ALL_NODES = [
  'load_runtime_context',
  'novel_context',
  'plan_chapter',
  'generate_draft',
  'check_consistency',
  'review',
  'rewrite',
  'commit',
]

export function AgentStatus({
  currentNode,
  executionHistory,
  progress,
  status = 'idle',
  generationId = '',
  draftLength = 0,
  tokenEventCount = 0,
  tokenCharCount = 0,
  tokenPreview = '',
  errorMessage = '',
  agentEvents = [],
}: AgentStatusProps) {
  const safeProgress = Math.min(100, Math.max(0, Math.round(progress)))
  const activeNodeLabel = currentNode ? getNodeLabel(currentNode) : 'Waiting for stream'
  const completedCount = new Set(executionHistory).size
  const rewriteCount = executionHistory.filter((node) => node === 'rewrite').length

  const getNodeStatus = (node: string) => {
    if (executionHistory.includes(node)) return 'completed'
    if (node === currentNode) return 'active'
    return 'pending'
  }

  return (
    <section className="agent-status" aria-label="Agent event stream">
      <div className="agent-status-header">
        <div>
          <h3>Agent Event Stream</h3>
          <p>{activeNodeLabel}</p>
        </div>
        <span className={`agent-status-pill status-${status}`}>{formatStatus(status)}</span>
      </div>

      <div className="agent-progress" aria-label={`Workflow progress ${safeProgress}%`}>
        <div className="agent-progress-track">
          <div className="agent-progress-fill" style={{ width: `${safeProgress}%` }} />
        </div>
        <span>{safeProgress}%</span>
      </div>

      <div className="agent-metrics" aria-label="Generation metrics">
        <Metric label="Generation" value={generationId ? shortId(generationId) : 'Pending'} />
        <Metric label="Nodes done" value={`${completedCount}/${ALL_NODES.length}`} />
        <Metric label="Token events" value={tokenEventCount.toLocaleString()} />
        <Metric label="Draft chars" value={(draftLength || tokenCharCount).toLocaleString()} />
      </div>

      <div className="agent-node-strip" aria-label="Workflow nodes">
        {ALL_NODES.map((node) => {
          const nodeStatus = getNodeStatus(node)
          return (
            <div
              key={node}
              className={`agent-node-dot ${nodeStatus}`}
              title={getNodeLabel(node)}
              aria-label={`${getNodeLabel(node)} ${nodeStatus}`}
            >
              <span />
            </div>
          )
        })}
      </div>

      {tokenPreview && (
        <div className="agent-token-preview">
          <span>Latest token</span>
          <p>{tokenPreview}</p>
        </div>
      )}

      {errorMessage && (
        <div className="agent-error" role="alert">
          <span>Error</span>
          <p>{errorMessage}</p>
        </div>
      )}

      <div className="agent-events">
        <div className="agent-events-heading">
          <h4>Recent events</h4>
          <span>Last {Math.min(agentEvents.length, 20)}</span>
        </div>

        {agentEvents.length === 0 ? (
          <p className="agent-events-empty">No stream events yet.</p>
        ) : (
          <ol className="agent-event-list">
            {agentEvents.map((event) => (
              <li key={event.id} className={`agent-event event-${event.type}`}>
                <time>{event.timestamp}</time>
                <div>
                  <span>{formatEventType(event.type)}</span>
                  <strong>{event.label}</strong>
                  {event.detail && <p>{event.detail}</p>}
                </div>
              </li>
            ))}
          </ol>
        )}
      </div>

      {rewriteCount > 0 && (
        <div className="agent-rewrite-note">
          Rewrite pass ran {rewriteCount} {rewriteCount === 1 ? 'time' : 'times'}.
        </div>
      )}
    </section>
  )
}

function Metric({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="agent-metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  )
}

function getNodeLabel(node: string) {
  return NODE_LABELS[node] || node.replaceAll('_', ' ')
}

function shortId(id: string) {
  if (id.length <= 10) return id
  return `${id.slice(0, 6)}...${id.slice(-4)}`
}

function formatStatus(status: WorkflowStatus) {
  if (status === 'idle') return 'Idle'
  if (status === 'connecting') return 'Connecting'
  if (status === 'generating') return 'Generating'
  if (status === 'done') return 'Done'
  return 'Error'
}

function formatEventType(type: AgentEvent['type']) {
  return type.replaceAll('_', ' ')
}
