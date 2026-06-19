import type { Chapter, ChapterGeneration } from '../types'
import './LivePreview.css'

type Severity = 'P0' | 'P1' | 'P2' | 'INFO'

interface DisplayIssue {
  id: string
  source: string
  severity: Severity
  category: string
  message: string
  evidence?: string
  suggestion?: string
  blocking: boolean
}

interface LivePreviewProps {
  draft: string
  isGenerating: boolean
  status?: 'idle' | 'connecting' | 'generating' | 'done' | 'error'
  errorMessage?: string
  generationId?: string
  generation?: ChapterGeneration | null
  chapter?: Chapter | null
  runtimeHistory?: string[]
  confirming?: boolean
  onConfirmDraft?: (generationId: string) => void
}

export function LivePreview({
  draft,
  isGenerating,
  status = 'idle',
  errorMessage = '',
  generationId = '',
  generation,
  chapter,
  runtimeHistory = [],
  confirming = false,
  onConfirmDraft,
}: LivePreviewProps) {
  const wordCount = draft.length
  const activeGenerationId = generation?.id || generationId
  const workflowStage = normalizeStage(chapter?.workflowStage ?? chapter?.workflow_stage)
  const confirmed = Boolean(
    activeGenerationId
      && chapter?.lastGenerationId === activeGenerationId
      && isDraftConfirmedStage(workflowStage),
  )
  const canConfirm = Boolean(
    activeGenerationId
      && draft.trim()
      && !isGenerating
      && !confirmed
      && (generation?.status?.toLowerCase() === 'succeeded' || status === 'done'),
  )

  const reviewIssues = getIssues(generation?.reviewReport, 'Review')
  const consistencyIssues = getIssues(generation?.consistencyReport, 'Consistency')
  const issues = [...reviewIssues, ...consistencyIssues]
  const repair = getRepairInfo(generation)
  const history = getHistoryItems(generation?.executionHistory, runtimeHistory)

  return (
    <div className="live-preview">
      <div className="preview-header">
        <div>
          <h3>Chapter Draft</h3>
          <p>{activeGenerationId ? `Generation ${shortId(activeGenerationId)}` : 'No generation selected'}</p>
        </div>
        <div className="preview-meta">
          <span className="word-count">{wordCount.toLocaleString()} chars</span>
          {isGenerating && <span className="typing-indicator">Generating</span>}
          {confirmed && <span className="confirmed-pill">Draft confirmed</span>}
          {onConfirmDraft && activeGenerationId && (
            <button
              type="button"
              className="confirm-draft-button"
              onClick={() => activeGenerationId && onConfirmDraft(activeGenerationId)}
              disabled={!canConfirm || confirming}
            >
              {confirming ? 'Confirming' : confirmed ? 'Confirmed' : 'Confirm draft'}
            </button>
          )}
        </div>
      </div>

      {status === 'error' && errorMessage && <div className="preview-error">{errorMessage}</div>}

      <div className="preview-layout">
        <section className="preview-content" aria-label="Generated draft">
          {draft ? (
            <div className="draft-text">
              {draft.split('\n').map((line, i) => (
                <p key={i}>{line || <br />}</p>
              ))}
              {isGenerating && <span className="cursor-blink">|</span>}
            </div>
          ) : (
            <div className="empty-state">
              <p>No draft yet.</p>
              <p className="hint">Confirm the outline, then generate the selected chapter.</p>
            </div>
          )}
        </section>

        <aside className="draft-inspector" aria-label="Draft review and repair">
          <section className="inspector-section">
            <div className="inspector-heading">
              <h4>Issues</h4>
              <span>{issueCountLabel(issues)}</span>
            </div>
            {issues.length > 0 ? (
              <div className="issue-list">
                {issues.map((issue) => (
                  <article key={issue.id} className={`issue-card severity-${issue.severity.toLowerCase()}`}>
                    <div className="issue-title">
                      <span>{issue.severity}</span>
                      <strong>{issue.source}</strong>
                      {issue.category && <em>{issue.category}</em>}
                    </div>
                    <p>{issue.message}</p>
                    {issue.evidence && <blockquote>{issue.evidence}</blockquote>}
                    {issue.suggestion && <small>{issue.suggestion}</small>}
                  </article>
                ))}
              </div>
            ) : (
              <p className="inspector-empty">
                {generation ? 'No review or consistency issues were returned.' : 'Review results will appear after a generation is selected.'}
              </p>
            )}
          </section>

          <section className="inspector-section">
            <div className="inspector-heading">
              <h4>Repair</h4>
              <span>{repair ? repair.strategy || 'recorded' : 'none'}</span>
            </div>
            {repair ? (
              <div className="repair-summary">
                <p>{repair.summary}</p>
                <dl>
                  <div>
                    <dt>Repaired</dt>
                    <dd>{repair.repairedIds.length ? repair.repairedIds.join(', ') : 'None'}</dd>
                  </div>
                  <div>
                    <dt>Remaining</dt>
                    <dd>{repair.remainingIds.length ? repair.remainingIds.join(', ') : 'None'}</dd>
                  </div>
                </dl>
              </div>
            ) : (
              <p className="inspector-empty">No repair result has been returned for this draft.</p>
            )}
          </section>

          <section className="inspector-section">
            <div className="inspector-heading">
              <h4>Node History</h4>
              <span>{history.length ? `${history.length} steps` : 'empty'}</span>
            </div>
            {history.length > 0 ? (
              <ol className="node-history">
                {history.map((item, index) => (
                  <li key={`${item}-${index}`}>{item}</li>
                ))}
              </ol>
            ) : (
              <p className="inspector-empty">No execution history is available yet.</p>
            )}
          </section>
        </aside>
      </div>
    </div>
  )
}

function getIssues(report: Record<string, unknown> | undefined, source: string): DisplayIssue[] {
  const rawIssues = Array.isArray(report?.issues) ? report.issues : []
  return rawIssues
    .filter(isRecord)
    .map((item, index) => ({
      id: getString(item.id) || getString(item.issueId) || `${source}-${index}`,
      source,
      severity: getSeverity(item.severity),
      category: getString(item.category) || getString(item.domain) || '',
      message: getString(item.message) || 'Issue returned without a message.',
      evidence: getString(item.evidence) || getLocationQuote(item.location),
      suggestion: getString(item.suggestion),
      blocking: Boolean(item.blocking),
    }))
}

function getRepairInfo(generation?: ChapterGeneration | null) {
  const report = generation?.repairResult || generation?.repairReport || generation?.autoRepairResult
  if (!isRecord(report)) return null

  return {
    summary:
      getString(report.repairSummary)
      || getString(report.summary)
      || getString(report.message)
      || 'Repair result returned without a summary.',
    repairedIds: getStringArray(report.repairedIssueIds),
    remainingIds: getStringArray(report.remainingIssueIds),
    strategy: getString(report.strategy),
  }
}

function getHistoryItems(
  executionHistory: Array<Record<string, unknown>> | undefined,
  runtimeHistory: string[],
) {
  if (executionHistory?.length) {
    return executionHistory.map((item) => {
      const node = getString(item.node) || getString(item.name) || getString(item.event) || 'step'
      const status = getString(item.status)
      return status ? `${node} (${status})` : node
    })
  }
  return runtimeHistory
}

function issueCountLabel(issues: DisplayIssue[]) {
  if (!issues.length) return 'clear'
  const counts = issues.reduce<Record<Severity, number>>(
    (acc, issue) => {
      acc[issue.severity] += 1
      return acc
    },
    { P0: 0, P1: 0, P2: 0, INFO: 0 },
  )
  return [`P0 ${counts.P0}`, `P1 ${counts.P1}`, `P2 ${counts.P2}`].join(' / ')
}

function getSeverity(value: unknown): Severity {
  return value === 'P0' || value === 'P1' || value === 'P2' ? value : 'INFO'
}

function getLocationQuote(value: unknown) {
  return isRecord(value) ? getString(value.quote) : undefined
}

function getString(value: unknown) {
  return typeof value === 'string' && value.trim() ? value.trim() : undefined
}

function getStringArray(value: unknown) {
  return Array.isArray(value) ? value.filter((item): item is string => typeof item === 'string' && Boolean(item.trim())) : []
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}

function normalizeStage(value?: string) {
  return (value || '').toLowerCase()
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

function shortId(value: string) {
  return value.slice(0, 8)
}
