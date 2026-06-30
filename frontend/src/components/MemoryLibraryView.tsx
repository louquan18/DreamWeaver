import { useEffect, useMemo, useState } from 'react'
import { listStoryMemories } from '../services/api'
import type { MemoryLibraryType, Story } from '../types'
import './MemoryLibraryView.css'

interface MemoryLibraryViewProps {
  story: Story | null
  type: MemoryLibraryType
}

const MEMORY_COPY: Record<MemoryLibraryType, { title: string; empty: string }> = {
  characters: {
    title: 'Character Memory',
    empty: 'No character memories are available for this novel yet.',
  },
  foreshadows: {
    title: 'Foreshadow Memory',
    empty: 'No foreshadow records are available for this novel yet.',
  },
  world: {
    title: 'World Memory',
    empty: 'No world-state memories are available for this novel yet.',
  },
  timeline: {
    title: 'Timeline Memory',
    empty: 'No timeline events are available for this novel yet.',
  },
}

export function MemoryLibraryView({ story, type }: MemoryLibraryViewProps) {
  const [items, setItems] = useState<unknown[]>([])
  const [raw, setRaw] = useState<unknown>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const copy = MEMORY_COPY[type]

  useEffect(() => {
    let cancelled = false

    async function loadMemories() {
      if (!story?.id) {
        setItems([])
        setRaw(null)
        setError('')
        return
      }

      setLoading(true)
      setError('')
      try {
        const data = await listStoryMemories(story.id, type)
        if (cancelled) return
        setItems(data.items)
        setRaw(data.raw)
      } catch (loadError) {
        if (cancelled) return
        setItems([])
        setRaw(null)
        setError(loadError instanceof Error ? loadError.message : `Failed to load ${type} memory`)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    void loadMemories()

    return () => {
      cancelled = true
    }
  }, [story?.id, type])

  const summary = useMemo(() => summarizeItems(items), [items])

  if (!story) {
    return (
      <section className="memory-library">
        <div className="memory-library-empty">Select a novel to inspect its memory library.</div>
      </section>
    )
  }

  return (
    <section className="memory-library" aria-label={copy.title}>
      <div className="memory-library-header">
        <div>
          <span>{loading ? 'Loading' : `${items.length} records`}</span>
          <h3>{copy.title}</h3>
          <p>{story.title}</p>
        </div>
        <button type="button" onClick={() => void reload(story.id, type, setLoading, setError, setItems, setRaw)}>
          Refresh
        </button>
      </div>

      {error && <div className="memory-library-message error">{error}</div>}

      {!error && items.length === 0 && !loading && (
        <div className="memory-library-empty">{copy.empty}</div>
      )}

      {!error && items.length > 0 && (
        <>
          <div className="memory-library-metrics">
            <span>
              <strong>{items.length}</strong>
              Records
            </span>
            <span>
              <strong>{summary.withStatus}</strong>
              With status
            </span>
            <span>
              <strong>{summary.withUpdatedAt}</strong>
              Updated
            </span>
          </div>

          <div className="memory-library-list">
            {items.map((item, index) => (
              <article key={itemKey(item, index)} className="memory-library-card">
                <div className="memory-card-head">
                  <div>
                    <span>{recordStatus(item) || `Record ${index + 1}`}</span>
                    <h4>{recordTitle(item, index)}</h4>
                  </div>
                  <strong>{recordDate(item)}</strong>
                </div>
                <ReadableMemoryRecord item={item} type={type} />
                <details className="memory-card-raw">
                  <summary>Raw JSON</summary>
                  <pre>{formatRecord(item)}</pre>
                </details>
              </article>
            ))}
          </div>
        </>
      )}

      {!error && items.length === 0 && Boolean(raw) && !Array.isArray(raw) && (
        <details className="memory-library-raw">
          <summary>Raw response</summary>
          <pre>{formatRecord(raw)}</pre>
        </details>
      )}
    </section>
  )
}

function ReadableMemoryRecord({
  item,
  type,
}: {
  item: unknown
  type: MemoryLibraryType
}) {
  const record = readRecord(item)
  const lines = readableLines(record, type)
  const source = sourceLine(record)

  return (
    <div className="memory-readable">
      {lines.map((line) => (
        <p key={`${line.label}-${line.value}`}>
          <span>{line.label}</span>
          {line.value}
        </p>
      ))}
      {source && (
        <p className="memory-readable-source">
          <span>Source</span>
          {source}
        </p>
      )}
    </div>
  )
}

function readableLines(record: Record<string, unknown>, type: MemoryLibraryType) {
  if (type === 'characters') return characterLines(record)
  if (type === 'foreshadows') return foreshadowLines(record)
  if (type === 'world') return worldLines(record)
  return timelineLines(record)
}

function characterLines(record: Record<string, unknown>) {
  const latestChange = readRecord(record.latestChange)
  const character = readRecord(record.character)
  return compactLines([
    line('Identity', text(record.name) || text(character.name) || text(record.characterName)),
    line('Current state', stateText(record.currentState) || text(record.after) || text(latestChange.after)),
    line('Motivation', text(record.motivation) || text(character.motivation) || text(latestChange.motivation)),
    line('Impact', text(record.impact) || text(latestChange.impact)),
    line('Related cast', listText(record.relatedCharacters) || listText(latestChange.relatedCharacters)),
  ])
}

function foreshadowLines(record: Record<string, unknown>) {
  return compactLines([
    line('Clue', text(record.content) || text(record.description) || text(record.summary)),
    line('Status', text(record.status) || text(record.lifecycle) || text(record.operation)),
    line('Payoff hint', text(record.payoffHint) || text(record.payoff_hint) || text(record.trigger) || text(record.resolution)),
    line('Importance', text(record.importance) || text(record.attentionStatus)),
  ])
}

function worldLines(record: Record<string, unknown>) {
  return compactLines([
    line('Subject', text(record.subject) || text(record.name) || text(record.title)),
    line('Type', text(record.subjectType) || text(record.type) || text(record.kind)),
    line('Rule', text(record.description) || text(record.rule) || text(record.summary)),
    line('Impact', text(record.impact) || text(record.after)),
  ])
}

function timelineLines(record: Record<string, unknown>) {
  return compactLines([
    line('Event', text(record.event) || text(record.summary) || text(record.description)),
    line('Outcome', text(record.outcome) || text(record.after) || text(record.result)),
    line('Importance', text(record.importance)),
    line('Causal link', text(record.causalLink) || text(record.causal_link) || text(record.cause)),
  ])
}

function sourceLine(record: Record<string, unknown>) {
  const chapter = text(record.chapterNumber) || text(record.chapter_number)
  const chapterId = shortId(text(record.chapterId) || text(record.chapter_id))
  const changeSet = shortId(text(record.changeSetId) || text(record.change_set_id))
  const parts = [
    chapter ? `Chapter ${chapter}` : '',
    chapterId ? `chapter ${chapterId}` : '',
    changeSet ? `change set ${changeSet}` : '',
  ].filter(Boolean)
  return parts.join(' / ')
}

function line(label: string, value: string) {
  return { label, value }
}

function compactLines(lines: Array<{ label: string; value: string }>) {
  const visible = lines.filter((item) => item.value)
  return visible.length ? visible : [line('Note', 'No readable summary fields were returned for this record.')]
}

function stateText(value: unknown): string {
  const record = readRecord(value)
  if (Object.keys(record).length === 0) return text(value)
  return Object.entries(record)
    .map(([key, item]) => `${humanizeKey(key)}: ${text(item)}`)
    .filter((item) => !item.endsWith(': '))
    .join('; ')
}

function listText(value: unknown): string {
  if (!Array.isArray(value)) return ''
  return value
    .map((item) => {
      if (typeof item === 'string') return item
      const record = readRecord(item)
      return text(record.name) || text(record.characterName) || text(record.id) || text(item)
    })
    .filter(Boolean)
    .join(', ')
}

function humanizeKey(value: string) {
  return value
    .replaceAll('_', ' ')
    .replace(/([a-z])([A-Z])/g, '$1 $2')
    .toLowerCase()
}

function shortId(value: string) {
  if (!value) return ''
  return value.length > 8 ? value.slice(0, 8) : value
}

async function reload(
  storyId: string,
  type: MemoryLibraryType,
  setLoading: (value: boolean) => void,
  setError: (value: string) => void,
  setItems: (value: unknown[]) => void,
  setRaw: (value: unknown) => void,
) {
  setLoading(true)
  setError('')
  try {
    const data = await listStoryMemories(storyId, type)
    setItems(data.items)
    setRaw(data.raw)
  } catch (error) {
    setItems([])
    setRaw(null)
    setError(error instanceof Error ? error.message : `Failed to load ${type} memory`)
  } finally {
    setLoading(false)
  }
}

function summarizeItems(items: unknown[]): { withStatus: number; withUpdatedAt: number } {
  return items.reduce<{ withStatus: number; withUpdatedAt: number }>(
    (acc, item) => {
      const record = readRecord(item)
      if (record.status) acc.withStatus += 1
      if (record.updatedAt || record.updated_at) acc.withUpdatedAt += 1
      return acc
    },
    { withStatus: 0, withUpdatedAt: 0 },
  )
}

function itemKey(item: unknown, index: number) {
  const record = readRecord(item)
  return text(record.id) || text(record.memoryId) || text(record.memory_id) || `memory-${index}`
}

function recordTitle(item: unknown, index: number) {
  const record = readRecord(item)
  return (
    text(record.name)
    || text(record.title)
    || text(record.summary)
    || text(record.event)
    || text(record.description)
    || `Memory record ${index + 1}`
  )
}

function recordStatus(item: unknown) {
  const record = readRecord(item)
  return text(record.status) || text(record.type) || text(record.kind)
}

function recordDate(item: unknown) {
  const record = readRecord(item)
  const value = text(record.updatedAt) || text(record.updated_at) || text(record.createdAt) || text(record.created_at)
  if (!value) return 'No date'
  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp)) return value
  return new Intl.DateTimeFormat(undefined, {
    month: 'short',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(timestamp)
}

function formatRecord(value: unknown) {
  if (typeof value === 'string') return value
  return JSON.stringify(value, null, 2) || ''
}

function readRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value)
    ? value as Record<string, unknown>
    : {}
}

function text(value: unknown) {
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  return typeof value === 'string' && value.trim() ? value.trim() : ''
}
