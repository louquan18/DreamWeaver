import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  confirmChapterGeneration,
  getChapterGeneration,
  listChapterGenerations,
} from '../services/api'
import type { Chapter, ChapterGeneration } from '../types'
import './GenerationHistory.css'

interface GenerationHistoryProps {
  storyId?: string
  chapterId?: string
  refreshKey: number
  onGenerationSelected: (generation: ChapterGeneration | null) => void
  onConfirmed: (chapter: Chapter) => void
}

export function GenerationHistory({
  storyId,
  chapterId,
  refreshKey,
  onGenerationSelected,
  onConfirmed,
}: GenerationHistoryProps) {
  const [items, setItems] = useState<ChapterGeneration[]>([])
  const [selectedId, setSelectedId] = useState('')
  const [detail, setDetail] = useState<ChapterGeneration | null>(null)
  const [loading, setLoading] = useState(false)
  const [confirmingId, setConfirmingId] = useState('')
  const [error, setError] = useState('')

  const selectedSummary = useMemo(
    () => items.find((item) => item.id === selectedId),
    [items, selectedId],
  )

  const loadHistory = useCallback(async () => {
    if (!storyId || !chapterId) {
      setItems([])
      setSelectedId('')
      setDetail(null)
      onGenerationSelected(null)
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = await listChapterGenerations(storyId, chapterId)
      setItems(data)
      if (data.length === 0) {
        setSelectedId('')
        setDetail(null)
        onGenerationSelected(null)
      }
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load history')
    } finally {
      setLoading(false)
    }
  }, [chapterId, onGenerationSelected, storyId])

  const loadDetail = useCallback(async (generationId: string) => {
    if (!storyId || !chapterId) return

    setSelectedId(generationId)
    setError('')
    try {
      const data = await getChapterGeneration(storyId, chapterId, generationId)
      setDetail(data)
      onGenerationSelected(data)
    } catch (loadError) {
      setError(loadError instanceof Error ? loadError.message : 'Failed to load generation')
    }
  }, [chapterId, onGenerationSelected, storyId])

  const handleConfirm = useCallback(async (generationId: string) => {
    if (!storyId || !chapterId) return

    setError('')
    setConfirmingId(generationId)
    try {
      const chapter = await confirmChapterGeneration(storyId, chapterId, generationId)
      onConfirmed(chapter)
      await loadHistory()
      await loadDetail(generationId)
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : 'Failed to confirm draft')
    } finally {
      setConfirmingId('')
    }
  }, [chapterId, loadDetail, loadHistory, onConfirmed, storyId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadHistory()
  }, [loadHistory, refreshKey])

  return (
    <div className="generation-history">
      <div className="history-header">
        <h3>Generation History</h3>
        <span>{loading ? 'Loading' : `${items.length} records`}</span>
      </div>

      {!storyId || !chapterId ? (
        <div className="history-empty">Select a chapter to view generated drafts.</div>
      ) : items.length === 0 ? (
        <div className="history-empty">No generation history yet.</div>
      ) : (
        <div className="history-list">
          {items.map((item) => (
            <div
              key={item.id}
              className={`history-item ${item.id === selectedId ? 'selected' : ''}`}
            >
              <button
                type="button"
                className="history-open"
                onClick={() => void loadDetail(item.id)}
              >
                <span className={`status-dot ${item.status}`} />
                <span className="history-main">
                  <strong>{labelStatus(item.status)}</strong>
                  <small>{formatDate(item.completedAt || item.createdAt)}</small>
                </span>
                <span className="history-side">
                  {(item.wordCount || 0).toLocaleString()}
                  {item.adopted && <em>Confirmed</em>}
                </span>
              </button>
              {item.status === 'succeeded' && !item.adopted && (
                <button
                  type="button"
                  className="adopt-button"
                  onClick={() => void handleConfirm(item.id)}
                  disabled={Boolean(confirmingId)}
                >
                  {confirmingId === item.id ? 'Confirming' : 'Confirm'}
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      {error && <div className="history-error">{error}</div>}

      {(detail || selectedSummary) && (
        <div className="history-detail">
          <div className="detail-meta">
            <span>{detail?.id || selectedSummary?.id}</span>
            <span>{(detail?.wordCount || selectedSummary?.wordCount || 0).toLocaleString()} chars</span>
          </div>
          <div className="detail-draft">
            {detail?.draft ? (
              detail.draft.split('\n').map((line, index) => (
                <p key={`${detail.id}-${index}`}>{line || <br />}</p>
              ))
            ) : (
              <p className="muted">Select a record to load the full generated text.</p>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

function labelStatus(status: string) {
  if (!status) return 'Unknown'
  return status.charAt(0).toUpperCase() + status.slice(1)
}

function formatDate(value?: string) {
  if (!value) return 'No timestamp'
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(value))
}
