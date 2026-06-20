import { useEffect, useMemo, useState } from 'react'
import {
  confirmMemoryChangeSet,
  extractMemoryChangeSet,
  freezeMemoryChangeSet,
  listMemoryChangeSets,
  updateMemoryChangeSet,
} from '../services/api'
import type { Chapter, MemoryChange, MemoryChangeSet, MemoryChangeType } from '../types'
import './MemoryChangeSetPanel.css'

interface MemoryChangeSetPanelProps {
  storyId?: string
  chapterId?: string
  chapter?: Chapter | null
  refreshKey?: number
  onChapterUpdated?: (chapter: Chapter) => void
}

const CHANGE_TYPES: Array<{
  key: MemoryChangeType
  label: string
  title: string
}> = [
  { key: 'timeline', label: 'Timeline', title: 'Timeline changes' },
  { key: 'character', label: 'Character', title: 'Character changes' },
  { key: 'world', label: 'World', title: 'World changes' },
  { key: 'foreshadow', label: 'Foreshadow', title: 'Foreshadow changes' },
]

const EDITABLE_STAGES = ['draft_confirmed', 'memory_extracting', 'memory_pending_confirmation']
const MEMORY_READY_STAGES = ['memory_confirmed']
const FINAL_STAGES = ['chapter_confirmed']

export function MemoryChangeSetPanel({
  storyId,
  chapterId,
  chapter,
  refreshKey = 0,
  onChapterUpdated,
}: MemoryChangeSetPanelProps) {
  const [changeSets, setChangeSets] = useState<MemoryChangeSet[]>([])
  const [selectedChangeSetId, setSelectedChangeSetId] = useState('')
  const [activeType, setActiveType] = useState<MemoryChangeType>('timeline')
  const [drafts, setDrafts] = useState<Record<MemoryChangeType, string>>(emptyDrafts())
  const [loading, setLoading] = useState(false)
  const [working, setWorking] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const canLoad = Boolean(storyId && chapterId)
  const workflowStage = normalizeStage(chapter?.workflowStage ?? chapter?.workflow_stage)
  const draftConfirmed = isDraftConfirmedStage(workflowStage)
  const canExtract = canLoad && EDITABLE_STAGES.includes(workflowStage)
  const canEdit = canLoad && EDITABLE_STAGES.includes(workflowStage)
  const canConfirm = canEdit && selectedChangeSetId && activeChangeSetStatus(changeSets, selectedChangeSetId) !== 'confirmed'
  const canFreeze = canLoad && selectedChangeSetId && MEMORY_READY_STAGES.includes(workflowStage)
  const frozen = FINAL_STAGES.includes(workflowStage)

  const selectedChangeSet = useMemo(
    () => changeSets.find((changeSet) => changeSet.id === selectedChangeSetId) || null,
    [changeSets, selectedChangeSetId],
  )

  const counts = useMemo(() => {
    const source = selectedChangeSet
    return CHANGE_TYPES.reduce<Record<MemoryChangeType, number>>((acc, item) => {
      acc[item.key] = source ? getChanges(source, item.key).length : 0
      return acc
    }, { timeline: 0, character: 0, world: 0, foreshadow: 0 })
  }, [selectedChangeSet])

  async function loadChangeSets() {
    if (!storyId || !chapterId || !draftConfirmed) {
      setChangeSets([])
      setSelectedChangeSetId('')
      setDrafts(emptyDrafts())
      setError('')
      setNotice('')
      return
    }

    setLoading(true)
    setError('')
    try {
      const data = sortChangeSets(await listMemoryChangeSets(storyId, chapterId))
      setChangeSets(data)
      setSelectedChangeSetId((current) => {
        if (data.some((changeSet) => changeSet.id === current)) return current
        return pickDefaultChangeSet(data)?.id || ''
      })
    } catch (loadError) {
      setChangeSets([])
      setSelectedChangeSetId('')
      setError(loadError instanceof Error ? loadError.message : 'Failed to load memory changes')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadChangeSets()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [storyId, chapterId, workflowStage, refreshKey])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDrafts(buildDrafts(selectedChangeSet))
    setError('')
    setNotice('')
  }, [selectedChangeSet])

  async function handleExtract() {
    if (!storyId || !chapterId || working || !canExtract) return

    setWorking(true)
    setError('')
    setNotice('')
    try {
      const result = await extractMemoryChangeSet(storyId, chapterId)
      const changeSet = result.memoryChangeSet || result.memory_change_set
      if (changeSet?.id) {
        setChangeSets((current) => sortChangeSets(upsertChangeSet(current, changeSet)))
        setSelectedChangeSetId(changeSet.id)
      }
      if (result.chapter) {
        onChapterUpdated?.(result.chapter)
      } else if (chapter) {
        onChapterUpdated?.({ ...chapter, workflowStage: 'memory_pending_confirmation' })
      }
      setNotice('Memory changes extracted. Review the JSON changes before confirming.')
    } catch (extractError) {
      setError(extractError instanceof Error ? extractError.message : 'Failed to extract memory changes')
    } finally {
      setWorking(false)
    }
  }

  async function handleSave() {
    if (!storyId || !chapterId || !selectedChangeSetId || working || !canEdit) return

    const parsed = parseDrafts(drafts)
    if (!parsed.ok) {
      setError(parsed.message)
      return
    }

    setWorking(true)
    setError('')
    setNotice('')
    try {
      const saved = await updateMemoryChangeSet(storyId, chapterId, selectedChangeSetId, {
        timelineChanges: parsed.value.timeline,
        timeline_changes: parsed.value.timeline,
        characterChanges: parsed.value.character,
        character_changes: parsed.value.character,
        worldChanges: parsed.value.world,
        world_changes: parsed.value.world,
        foreshadowChanges: parsed.value.foreshadow,
        foreshadow_changes: parsed.value.foreshadow,
      })
      setChangeSets((current) => sortChangeSets(upsertChangeSet(current, saved)))
      setSelectedChangeSetId(saved.id)
      setNotice('Memory changes saved.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save memory changes')
    } finally {
      setWorking(false)
    }
  }

  async function handleConfirm() {
    if (!storyId || !chapterId || !selectedChangeSetId || working || !canConfirm) return

    const parsed = parseDrafts(drafts)
    if (!parsed.ok) {
      setError(parsed.message)
      return
    }

    setWorking(true)
    setError('')
    setNotice('')
    try {
      await updateMemoryChangeSet(storyId, chapterId, selectedChangeSetId, {
        timelineChanges: parsed.value.timeline,
        timeline_changes: parsed.value.timeline,
        characterChanges: parsed.value.character,
        character_changes: parsed.value.character,
        worldChanges: parsed.value.world,
        world_changes: parsed.value.world,
        foreshadowChanges: parsed.value.foreshadow,
        foreshadow_changes: parsed.value.foreshadow,
      })
      const result = await confirmMemoryChangeSet(storyId, chapterId, selectedChangeSetId)
      const changeSet = result.memoryChangeSet || result.memory_change_set
      if (changeSet?.id) {
        setChangeSets((current) => sortChangeSets(upsertChangeSet(current, changeSet)))
        setSelectedChangeSetId(changeSet.id)
      }
      if (result.chapter) {
        onChapterUpdated?.(result.chapter)
      } else if (chapter) {
        onChapterUpdated?.({ ...chapter, workflowStage: 'memory_confirmed' })
      }
      setNotice('Memory changes confirmed. Chapter freeze is now available.')
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : 'Failed to confirm memory changes')
    } finally {
      setWorking(false)
    }
  }

  async function handleFreeze() {
    if (!storyId || !chapterId || !selectedChangeSetId || working || !canFreeze) return

    setWorking(true)
    setError('')
    setNotice('')
    try {
      const result = await freezeMemoryChangeSet(storyId, chapterId, selectedChangeSetId)
      const changeSet = result.memoryChangeSet || result.memory_change_set
      if (changeSet?.id) {
        setChangeSets((current) => sortChangeSets(upsertChangeSet(current, changeSet)))
        setSelectedChangeSetId(changeSet.id)
      }
      onChapterUpdated?.(result.chapter)
      setNotice('Chapter frozen.')
    } catch (freezeError) {
      setError(freezeError instanceof Error ? freezeError.message : 'Failed to freeze chapter')
    } finally {
      setWorking(false)
    }
  }

  function handleAddChange(type: MemoryChangeType) {
    updateDraftArray(type, (items) => [...items, {}])
  }

  function handleRemoveChange(type: MemoryChangeType, index: number) {
    updateDraftArray(type, (items) => items.filter((_, itemIndex) => itemIndex !== index))
  }

  function updateDraftArray(type: MemoryChangeType, updater: (items: MemoryChange[]) => MemoryChange[]) {
    const parsed = parseJsonArray(drafts[type], type)
    if (!parsed.ok) {
      setError(parsed.message)
      return
    }

    setDrafts((current) => ({
      ...current,
      [type]: stringifyJson(updater(parsed.value)),
    }))
    setError('')
    setNotice('')
  }

  return (
    <section className={`memory-panel ${frozen ? 'frozen' : ''}`} aria-label="Memory change set panel">
      <div className="memory-panel-header">
        <div>
          <span className="memory-kicker">Memory board</span>
          <h2>Chapter memory confirmation</h2>
        </div>
        <div className="memory-header-actions">
          {draftConfirmed && (
            <button type="button" onClick={loadChangeSets} disabled={!canLoad || loading || working}>
              {loading ? 'Loading' : 'Refresh'}
            </button>
          )}
          {canExtract && (
            <button type="button" onClick={handleExtract} disabled={working}>
              {working ? 'Working' : changeSets.length ? 'Extract again' : 'Extract'}
            </button>
          )}
        </div>
      </div>

      {!canLoad && (
        <div className="memory-empty">Select a novel and chapter to review memory changes.</div>
      )}

      {canLoad && !draftConfirmed && (
        <div className="memory-empty">
          Confirm the chapter draft before extracting memory changes.
        </div>
      )}

      {canLoad && draftConfirmed && (
        <>
          <div className={`memory-stage-strip stage-${workflowStage || 'unknown'}`}>
            <div>
              <span className="memory-kicker">Stage</span>
              <strong>{formatStage(workflowStage)}</strong>
            </div>
            <p>{stageMessage(workflowStage, changeSets.length)}</p>
          </div>

          {error && <div className="memory-message error">{error}</div>}
          {notice && <div className="memory-message success">{notice}</div>}

          {changeSets.length === 0 && !loading && (
            <div className="memory-empty">
              No memory change set has been extracted for this chapter yet.
            </div>
          )}

          {changeSets.length > 0 && (
            <>
              <div className="memory-toolbar">
                <label>
                  <span>Change set</span>
                  <select
                    value={selectedChangeSetId}
                    onChange={(event) => setSelectedChangeSetId(event.target.value)}
                    disabled={working}
                  >
                    {changeSets.map((changeSet) => (
                      <option key={changeSet.id} value={changeSet.id}>
                        {changeSetLabel(changeSet)}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="memory-status-metrics" aria-label="Memory change counts">
                  {CHANGE_TYPES.map((item) => (
                    <span key={item.key}>{item.label} {counts[item.key]}</span>
                  ))}
                </div>
              </div>

              <div className="memory-tabs" role="tablist" aria-label="Memory change types">
                {CHANGE_TYPES.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className={item.key === activeType ? 'active' : ''}
                    onClick={() => setActiveType(item.key)}
                    role="tab"
                    aria-selected={item.key === activeType}
                  >
                    {item.label}
                    <span>{counts[item.key]}</span>
                  </button>
                ))}
              </div>

              <div className="memory-editor">
                <div className="memory-editor-heading">
                  <div>
                    <span className="memory-kicker">JSON array</span>
                    <h3>{CHANGE_TYPES.find((item) => item.key === activeType)?.title}</h3>
                  </div>
                  <div className="memory-editor-actions">
                    <button
                      type="button"
                      onClick={() => handleAddChange(activeType)}
                      disabled={!canEdit || working}
                    >
                      Add empty change
                    </button>
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={!canEdit || working || !selectedChangeSetId}
                    >
                      {working ? 'Saving' : 'Save edits'}
                    </button>
                  </div>
                </div>

                <textarea
                  value={drafts[activeType]}
                  onChange={(event) => {
                    setDrafts((current) => ({ ...current, [activeType]: event.target.value }))
                    setError('')
                    setNotice('')
                  }}
                  rows={12}
                  spellCheck={false}
                  disabled={!canEdit || working || frozen}
                />

                <div className="memory-index-actions">
                  {Array.from({ length: counts[activeType] }).map((_, index) => (
                    <button
                      key={`${activeType}-${index}`}
                      type="button"
                      onClick={() => handleRemoveChange(activeType, index)}
                      disabled={!canEdit || working}
                    >
                      Remove #{index + 1}
                    </button>
                  ))}
                </div>
              </div>

              <div className="memory-final-actions">
                <p>
                  {selectedChangeSet
                    ? `Selected ${shortId(selectedChangeSet.id)} / ${selectedChangeSet.status || 'pending'}`
                    : 'Select a memory change set before continuing.'}
                </p>
                <div>
                  <button type="button" onClick={handleConfirm} disabled={!canConfirm || working}>
                    {working ? 'Working' : 'Confirm memory changes'}
                  </button>
                  <button type="button" onClick={handleFreeze} disabled={!canFreeze || working}>
                    {working ? 'Working' : frozen ? 'Frozen' : 'Freeze chapter'}
                  </button>
                </div>
              </div>
            </>
          )}
        </>
      )}
    </section>
  )
}

function emptyDrafts(): Record<MemoryChangeType, string> {
  return {
    timeline: '[]',
    character: '[]',
    world: '[]',
    foreshadow: '[]',
  }
}

function buildDrafts(changeSet: MemoryChangeSet | null): Record<MemoryChangeType, string> {
  if (!changeSet) return emptyDrafts()
  return {
    timeline: stringifyJson(getChanges(changeSet, 'timeline')),
    character: stringifyJson(getChanges(changeSet, 'character')),
    world: stringifyJson(getChanges(changeSet, 'world')),
    foreshadow: stringifyJson(getChanges(changeSet, 'foreshadow')),
  }
}

function getChanges(changeSet: MemoryChangeSet, type: MemoryChangeType): MemoryChange[] {
  const fromChanges = changeSet.changes?.[type]
  if (Array.isArray(fromChanges)) return fromChanges
  if (type === 'timeline') return changeSet.timelineChanges ?? changeSet.timeline_changes ?? []
  if (type === 'character') return changeSet.characterChanges ?? changeSet.character_changes ?? []
  if (type === 'world') return changeSet.worldChanges ?? changeSet.world_changes ?? []
  return changeSet.foreshadowChanges ?? changeSet.foreshadow_changes ?? []
}

function parseDrafts(drafts: Record<MemoryChangeType, string>):
  | { ok: true; value: Record<MemoryChangeType, MemoryChange[]> }
  | { ok: false; message: string } {
  const timeline = parseJsonArray(drafts.timeline, 'timeline')
  if (!timeline.ok) return timeline
  const character = parseJsonArray(drafts.character, 'character')
  if (!character.ok) return character
  const world = parseJsonArray(drafts.world, 'world')
  if (!world.ok) return world
  const foreshadow = parseJsonArray(drafts.foreshadow, 'foreshadow')
  if (!foreshadow.ok) return foreshadow
  return {
    ok: true,
    value: {
      timeline: timeline.value,
      character: character.value,
      world: world.value,
      foreshadow: foreshadow.value,
    },
  }
}

function parseJsonArray(text: string, type: MemoryChangeType):
  | { ok: true; value: MemoryChange[] }
  | { ok: false; message: string } {
  try {
    const parsed = JSON.parse(text)
    if (!Array.isArray(parsed)) {
      return { ok: false, message: `${type} changes must be a JSON array.` }
    }
    if (!parsed.every(isRecord)) {
      return { ok: false, message: `${type} changes must contain JSON objects only.` }
    }
    return { ok: true, value: parsed }
  } catch (error) {
    return {
      ok: false,
      message: error instanceof Error ? `${type} JSON is invalid: ${error.message}` : `${type} JSON is invalid.`,
    }
  }
}

function stringifyJson(value: MemoryChange[]) {
  return JSON.stringify(value, null, 2)
}

function upsertChangeSet(current: MemoryChangeSet[], next: MemoryChangeSet) {
  const exists = current.some((changeSet) => changeSet.id === next.id)
  if (exists) {
    return current.map((changeSet) => changeSet.id === next.id ? next : changeSet)
  }
  return [next, ...current]
}

function sortChangeSets(changeSets: MemoryChangeSet[]) {
  return [...changeSets].sort((left, right) => timestamp(right) - timestamp(left))
}

function pickDefaultChangeSet(changeSets: MemoryChangeSet[]) {
  return changeSets.find((changeSet) => normalizeStage(changeSet.status) === 'pending')
    || changeSets.find((changeSet) => normalizeStage(changeSet.status) === 'confirmed')
    || changeSets[0]
}

function timestamp(changeSet: MemoryChangeSet) {
  const value = changeSet.updatedAt
    || changeSet.updated_at
    || changeSet.createdAt
    || changeSet.created_at
    || ''
  return value ? Date.parse(value) || 0 : 0
}

function activeChangeSetStatus(changeSets: MemoryChangeSet[], selectedId: string) {
  return normalizeStage(changeSets.find((changeSet) => changeSet.id === selectedId)?.status)
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

function normalizeStage(value?: string) {
  return (value || '').toLowerCase()
}

function formatStage(value: string) {
  if (!value) return 'chapter created'
  return value.replaceAll('_', ' ')
}

function stageMessage(stage: string, count: number) {
  if (stage === 'draft_confirmed') return 'Extract memory changes from the confirmed draft.'
  if (stage === 'memory_extracting') return 'Memory extraction is in progress or ready to run again.'
  if (stage === 'memory_pending_confirmation') return 'Review and edit pending memory changes before confirming.'
  if (stage === 'memory_confirmed') return 'Memory changes are confirmed. Freeze the chapter to lock it.'
  if (stage === 'chapter_confirmed') return 'Chapter is frozen. Memory editing is locked.'
  return count ? 'Memory changes are available for this chapter.' : 'No memory changes are available yet.'
}

function changeSetLabel(changeSet: MemoryChangeSet) {
  const date = changeSet.updatedAt || changeSet.updated_at || changeSet.createdAt || changeSet.created_at
  const dateLabel = date ? new Date(date).toLocaleString() : 'no timestamp'
  return `${shortId(changeSet.id)} / ${changeSet.status || 'pending'} / ${dateLabel}`
}

function shortId(value: string) {
  return value.slice(0, 8)
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null
}
