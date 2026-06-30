import type { Chapter, ChapterGeneration } from '../types'
import './LivePreview.css'

type Severity = 'P0' | 'P1' | 'P2' | 'INFO'
type ConfirmationState = 'generating' | 'confirmed' | 'blocked' | 'ready' | 'waiting'
type ReadinessTone = 'muted' | 'active' | 'success' | 'danger'

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

interface IssueSummary {
  total: number
  blocking: number
  advisory: number
  bySource: Record<string, number>
  bySeverity: Record<Severity, number>
}

interface ConfirmationReadiness {
  state: ConfirmationState
  tone: ReadinessTone
  label: string
  detail: string
  buttonLabel: string
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
  const hasDraft = Boolean(draft.trim())
  const generationStatus = generation?.status?.toLowerCase()
  const generationLabel = generation?.status || status
  const hasSuccessfulGeneration = generationStatus === 'succeeded' || status === 'done'
  const workflowStage = normalizeStage(chapter?.workflowStage ?? chapter?.workflow_stage)
  const lastGenerationId = chapter?.lastGenerationId ?? chapter?.last_generation_id
  const confirmed = Boolean(
    activeGenerationId
      && (lastGenerationId === activeGenerationId || generation?.adopted)
      && isDraftConfirmedStage(workflowStage),
  )
  const reviewReport = getReport(generation, 'reviewReport', 'review_report')
  const consistencyReport = getReport(generation, 'consistencyReport', 'consistency_report')
  const hasQualityReports = Boolean(reviewReport || consistencyReport)
  const reviewIssues = getIssues(reviewReport, 'Review')
  const consistencyIssues = getIssues(consistencyReport, 'Consistency')
  const issues = [...reviewIssues, ...consistencyIssues]
  const issueSummary = getIssueSummary(issues)
  const blockingIssues = issues.filter((issue) => issue.blocking)
  const advisoryIssues = issues.filter((issue) => !issue.blocking)
  const readiness = getConfirmationReadiness({
    activeGenerationId,
    blockingCount: issueSummary.blocking,
    confirmed,
    generationLabel,
    hasDraft,
    hasQualityReports,
    hasSuccessfulGeneration,
    isGenerating,
  })
  const repair = getRepairInfo(generation)
  const history = getHistoryItems(generation?.executionHistory, runtimeHistory)
  const canConfirm = readiness.state === 'ready' && !confirming

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
              className={`confirm-draft-button confirm-state-${readiness.state}`}
              onClick={() => canConfirm && onConfirmDraft(activeGenerationId)}
              disabled={!canConfirm}
              aria-describedby="draft-confirmation-status"
            >
              {confirming ? 'Confirming' : readiness.buttonLabel}
            </button>
          )}
        </div>
      </div>

      {status === 'error' && errorMessage && <div className="preview-error">{errorMessage}</div>}

      <section
        id="draft-confirmation-status"
        className={`draft-readiness readiness-${readiness.tone}`}
        aria-live="polite"
      >
        <div>
          <span className="readiness-kicker">Confirmation status</span>
          <strong>{readiness.label}</strong>
          <p>{readiness.detail}</p>
        </div>
        <div className="readiness-checks" aria-label="Draft confirmation checks">
          <span className={hasSuccessfulGeneration ? 'check-ok' : 'check-wait'}>
            Generation: {hasSuccessfulGeneration ? 'successful' : generationLabel}
          </span>
          <span className={hasDraft ? 'check-ok' : 'check-wait'}>
            Draft: {hasDraft ? 'available' : 'empty'}
          </span>
          <span className={issueSummary.blocking ? 'check-blocked' : 'check-ok'}>
            Blocking issues: {issueSummary.blocking}
          </span>
          <span className={hasQualityReports ? 'check-ok' : 'check-wait'}>
            Reports: {hasQualityReports ? 'attached' : 'waiting'}
          </span>
        </div>
      </section>

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
              <span>{issueCountLabel(issueSummary)}</span>
            </div>
            <ReportSummary
              reviewReport={reviewReport}
              consistencyReport={consistencyReport}
            />
            {issues.length > 0 && (
              <div className="issue-summary" aria-label="Issue summary">
                <span>
                  <strong>{issueSummary.blocking}</strong>
                  Blocking
                </span>
                <span>
                  <strong>{issueSummary.advisory}</strong>
                  Non-blocking
                </span>
                <span>
                  <strong>{issueSummary.bySource.Review || 0}</strong>
                  Review
                </span>
                <span>
                  <strong>{issueSummary.bySource.Consistency || 0}</strong>
                  Consistency
                </span>
              </div>
            )}
            {issues.length > 0 ? (
              <div className="issue-list">
                {blockingIssues.length > 0 && (
                  <IssueGroup title="Blocking" issues={blockingIssues} />
                )}
                {advisoryIssues.length > 0 && (
                  <IssueGroup title="Non-blocking" issues={advisoryIssues} />
                )}
              </div>
            ) : (
              <p className="inspector-empty">
                {getIssueEmptyMessage(Boolean(generation), hasQualityReports)}
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

function getIssueEmptyMessage(hasGeneration: boolean, hasQualityReports: boolean) {
  if (!hasGeneration) return 'Review results will appear after a generation is selected.'
  if (!hasQualityReports) return 'Quality reports have not been attached to this generation yet.'
  return 'Quality reports are clear; no review or consistency issues were returned.'
}

function ReportSummary({
  reviewReport,
  consistencyReport,
}: {
  reviewReport?: Record<string, unknown>
  consistencyReport?: Record<string, unknown>
}) {
  if (!reviewReport && !consistencyReport) return null

  const reviewScore =
    getNumber(reviewReport?.overallScore)
    ?? getNumber(reviewReport?.overall_score)
    ?? getNumber(reviewReport?.score)
  const reviewSummary = getString(reviewReport?.summary)
  const consistencySummary = getString(consistencyReport?.summary)
  const checkedRules = getArrayCount(consistencyReport?.checkedRuleIds ?? consistencyReport?.checked_rule_ids)
  const passedRules = getArrayCount(consistencyReport?.passedRuleIds ?? consistencyReport?.passed_rule_ids)

  return (
    <div className="report-summary" aria-label="Draft quality reports">
      {reviewReport && (
        <article>
          <div>
            <span>Review</span>
            {reviewScore !== undefined && <strong>{reviewScore}</strong>}
          </div>
          {reviewSummary && <p>{reviewSummary}</p>}
        </article>
      )}
      {consistencyReport && (
        <article>
          <div>
            <span>Consistency</span>
            {(checkedRules > 0 || passedRules > 0) && (
              <strong>{passedRules}/{checkedRules || passedRules}</strong>
            )}
          </div>
          {consistencySummary && <p>{consistencySummary}</p>}
        </article>
      )}
    </div>
  )
}

function IssueGroup({ title, issues }: { title: string, issues: DisplayIssue[] }) {
  return (
    <div className="issue-group">
      <div className="issue-group-title">
        <span>{title}</span>
        <em>{issues.length}</em>
      </div>
      {issues.map((issue) => (
        <article
          key={issue.id}
          className={`issue-card severity-${issue.severity.toLowerCase()} ${issue.blocking ? 'is-blocking' : 'is-advisory'}`}
        >
          <div className="issue-title">
            <span className="severity-badge">{issue.severity}</span>
            <span className={`source-badge source-${issue.source.toLowerCase()}`}>{issue.source}</span>
            <strong>{issue.blocking ? 'Blocking' : 'Non-blocking'}</strong>
            {issue.category && <em>{issue.category}</em>}
          </div>
          <p>{issue.message}</p>
          {issue.evidence && <blockquote>{issue.evidence}</blockquote>}
          {issue.suggestion && <small>{issue.suggestion}</small>}
        </article>
      ))}
    </div>
  )
}

function getReport(
  generation: ChapterGeneration | null | undefined,
  camelKey: 'reviewReport' | 'consistencyReport',
  snakeKey: 'review_report' | 'consistency_report',
) {
  const camelReport = generation?.[camelKey]
  if (isRecord(camelReport)) return camelReport
  const snakeReport = generation?.[snakeKey]
  return isRecord(snakeReport) ? snakeReport : undefined
}

function getIssues(report: Record<string, unknown> | undefined, source: string): DisplayIssue[] {
  const rawIssues = Array.isArray(report?.issues) ? report.issues : []
  return rawIssues
    .filter(isRecord)
    .map((item, index) => {
      const severity = getSeverity(item.severity)
      return {
        id: getString(item.id) || getString(item.issueId) || `${source}-${index}`,
        source,
        severity,
        category: getString(item.category) || getString(item.domain) || '',
        message: getString(item.message) || 'Issue returned without a message.',
        evidence: getString(item.evidence) || getLocationQuote(item.location),
        suggestion: getString(item.suggestion),
        blocking: Boolean(item.blocking) || severity === 'P0',
      }
    })
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

function getIssueSummary(issues: DisplayIssue[]): IssueSummary {
  return issues.reduce<IssueSummary>(
    (acc, issue) => {
      acc.total += 1
      acc.bySeverity[issue.severity] += 1
      acc.bySource[issue.source] = (acc.bySource[issue.source] || 0) + 1
      if (issue.blocking) {
        acc.blocking += 1
      } else {
        acc.advisory += 1
      }
      return acc
    },
    {
      total: 0,
      blocking: 0,
      advisory: 0,
      bySource: {},
      bySeverity: { P0: 0, P1: 0, P2: 0, INFO: 0 },
    },
  )
}

function issueCountLabel(summary: IssueSummary) {
  if (!summary.total) return 'clear'
  const severity = [
    `P0 ${summary.bySeverity.P0}`,
    `P1 ${summary.bySeverity.P1}`,
    `P2 ${summary.bySeverity.P2}`,
    `Info ${summary.bySeverity.INFO}`,
  ].join(' / ')
  return `${summary.blocking} blocking / ${severity}`
}

function getConfirmationReadiness({
  activeGenerationId,
  blockingCount,
  confirmed,
  generationLabel,
  hasDraft,
  hasQualityReports,
  hasSuccessfulGeneration,
  isGenerating,
}: {
  activeGenerationId: string
  blockingCount: number
  confirmed: boolean
  generationLabel: string
  hasDraft: boolean
  hasQualityReports: boolean
  hasSuccessfulGeneration: boolean
  isGenerating: boolean
}): ConfirmationReadiness {
  if (isGenerating) {
    return {
      state: 'generating',
      tone: 'active',
      label: 'Generation in progress',
      detail: 'Draft text is still streaming. Confirmation unlocks after the generation completes successfully.',
      buttonLabel: 'Generating',
    }
  }

  if (confirmed) {
    return {
      state: 'confirmed',
      tone: 'success',
      label: 'Draft already confirmed',
      detail: 'This generation has been adopted for the current chapter.',
      buttonLabel: 'Confirmed',
    }
  }

  if (!activeGenerationId) {
    return {
      state: 'waiting',
      tone: 'muted',
      label: 'No generation selected',
      detail: 'Select or complete a generation before confirming a draft.',
      buttonLabel: 'Confirm draft',
    }
  }

  if (!hasDraft) {
    return {
      state: 'waiting',
      tone: 'muted',
      label: 'Draft is empty',
      detail: 'Confirmation requires generated draft text.',
      buttonLabel: 'Confirm draft',
    }
  }

  if (!hasSuccessfulGeneration) {
    return {
      state: 'waiting',
      tone: 'muted',
      label: 'Waiting for a successful generation',
      detail: `Current generation status is ${generationLabel}. Confirm is available only after success.`,
      buttonLabel: 'Confirm draft',
    }
  }

  if (!hasQualityReports) {
    return {
      state: 'waiting',
      tone: 'danger',
      label: 'Waiting for quality reports',
      detail: 'The draft completed, but consistency and review reports have not been attached yet.',
      buttonLabel: 'Waiting',
    }
  }

  if (blockingCount > 0) {
    return {
      state: 'blocked',
      tone: 'danger',
      label: 'Confirmation blocked',
      detail: `${blockingCount} blocking issue${blockingCount === 1 ? '' : 's'} must be repaired or accepted before this draft can be confirmed.`,
      buttonLabel: 'Blocked',
    }
  }

  return {
    state: 'ready',
    tone: 'success',
    label: 'Ready to confirm',
    detail: 'Successful generation with draft text and no blocking issues.',
    buttonLabel: 'Confirm draft',
  }
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

function getNumber(value: unknown) {
  return typeof value === 'number' && Number.isFinite(value) ? value : undefined
}

function getArrayCount(value: unknown) {
  return Array.isArray(value) ? value.length : 0
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
