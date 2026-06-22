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
  help: string
}> = [
  {
    key: 'timeline',
    label: 'Timeline',
    title: 'Timeline changes',
    help: 'Events, ordering, scene outcomes, and causal links.',
  },
  {
    key: 'character',
    label: 'Character',
    title: 'Character changes',
    help: 'Character state, relationships, goals, wounds, and secrets.',
  },
  {
    key: 'world',
    label: 'World',
    title: 'World changes',
    help: 'Rules, places, factions, resources, and world-state facts.',
  },
  {
    key: 'foreshadow',
    label: 'Foreshadow',
    title: 'Foreshadow changes',
    help: 'Planted clues, strengthened hints, triggers, and payoffs.',
  },
  {
    key: 'conflicts',
    label: 'Conflicts',
    title: 'Conflict changes',
    help: 'Open contradictions, continuity risks, and unresolved tension.',
  },
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
  const canFreeze = canLoad && selectedChangeSetId && MEMORY_READY_STAGES.includes(workflowStage)
  const frozen = FINAL_STAGES.includes(workflowStage)

  const selectedChangeSet = useMemo(
    () => changeSets.find((changeSet) => changeSet.id === selectedChangeSetId) || null,
    [changeSets, selectedChangeSetId],
  )

  const selectedStatus = activeChangeSetStatus(changeSets, selectedChangeSetId)
  const savedDrafts = useMemo(() => buildDrafts(selectedChangeSet), [selectedChangeSet])
  const validation = useMemo(() => validateDrafts(drafts), [drafts])
  const allDraftsValid = CHANGE_TYPES.every((item) => validation[item.key].ok)
  const hasUnsavedDrafts = CHANGE_TYPES.some((item) => drafts[item.key] !== savedDrafts[item.key])
  const canSave = canEdit && Boolean(selectedChangeSetId) && hasUnsavedDrafts && allDraftsValid
  const canConfirm = canEdit && Boolean(selectedChangeSetId) && selectedStatus !== 'confirmed' && allDraftsValid
  const activeValidation = validation[activeType]
  const activeMeta = CHANGE_TYPES.find((item) => item.key === activeType) || CHANGE_TYPES[0]

  const counts = useMemo(() => {
    const source = selectedChangeSet
    return CHANGE_TYPES.reduce<Record<MemoryChangeType, number>>((acc, item) => {
      acc[item.key] = source ? getChanges(source, item.key).length : 0
      return acc
    }, emptyCounts())
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
      const saved = await updateMemoryChangeSet(
        storyId,
        chapterId,
        selectedChangeSetId,
        buildUpdateRequest(parsed.value),
      )
      setChangeSets((current) => sortChangeSets(upsertChangeSet(current, saved)))
      setSelectedChangeSetId(saved.id)
      setNotice('Memory changes saved. Review the staged changes before confirming.')
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
      await updateMemoryChangeSet(
        storyId,
        chapterId,
        selectedChangeSetId,
        buildUpdateRequest(parsed.value),
      )
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
      setNotice('Memory changes confirmed. Freeze is now available as the final chapter lock.')
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
      setNotice('Chapter frozen. Editing is locked for this chapter.')
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
                    <span key={item.key}>
                      <strong>{counts[item.key]}</strong>
                      {item.label}
                    </span>
                  ))}
                </div>
              </div>

              <div className="memory-tabs" role="tablist" aria-label="Memory change types">
                {CHANGE_TYPES.map((item) => (
                  <button
                    key={item.key}
                    type="button"
                    className={[
                      item.key === activeType ? 'active' : '',
                      validation[item.key].ok ? 'valid' : 'invalid',
                      drafts[item.key] !== savedDrafts[item.key] ? 'dirty' : '',
                    ].filter(Boolean).join(' ')}
                    onClick={() => setActiveType(item.key)}
                    role="tab"
                    aria-selected={item.key === activeType}
                  >
                    <span className="memory-tab-text">
                      {item.label}
                      <small>{validation[item.key].ok ? 'Valid array' : 'Invalid JSON'}</small>
                    </span>
                    <span className="memory-tab-count">{counts[item.key]}</span>
                  </button>
                ))}
              </div>

              <div className="memory-editor">
                <div className="memory-editor-heading">
                  <div>
                    <span className="memory-kicker">JSON array</span>
                    <h3>{activeMeta.title}</h3>
                    <p>{activeMeta.help}</p>
                  </div>
                  <div className="memory-editor-actions">
                    <button
                      type="button"
                      onClick={() => handleAddChange(activeType)}
                      disabled={!canEdit || working || !activeValidation.ok}
                    >
                      Add empty change
                    </button>
                    <button
                      type="button"
                      onClick={handleSave}
                      disabled={!canSave || working}
                    >
                      {working ? 'Saving' : 'Save edits'}
                    </button>
                  </div>
                </div>

                <div className="memory-json-state" aria-live="polite">
                  <span className={activeValidation.ok ? 'valid' : 'invalid'}>
                    {activeValidation.ok ? 'Valid JSON array' : activeValidation.message}
                  </span>
                  <span className={drafts[activeType] !== savedDrafts[activeType] ? 'dirty' : 'clean'}>
                    {drafts[activeType] !== savedDrafts[activeType] ? 'Unsaved edits' : 'Saved'}
                  </span>
                  <span>
                    {activeValidation.ok ? `${activeValidation.count} objects` : 'Fix before saving'}
                  </span>
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
                  aria-invalid={!activeValidation.ok}
                />

                <div className="memory-index-actions">
                  {activeValidation.ok && activeValidation.count === 0 && (
                    <span>No objects in this category.</span>
                  )}
                  {activeValidation.ok && Array.from({ length: activeValidation.count }).map((_, index) => (
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
                <div className="memory-final-copy">
                  <strong>
                    {selectedChangeSet
                      ? `${shortId(selectedChangeSet.id)} / ${selectedChangeSet.status || 'pending'}`
                      : 'No change set selected'}
                  </strong>
                  <p>{nextActionMessage(workflowStage, hasUnsavedDrafts, allDraftsValid)}</p>
                </div>
                <div className="memory-final-buttons">
                  <button type="button" onClick={handleConfirm} disabled={!canConfirm || working}>
                    {working ? 'Working' : hasUnsavedDrafts ? 'Save and confirm memory' : 'Confirm memory changes'}
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
    conflicts: '[]',
  }
}

function emptyCounts(): Record<MemoryChangeType, number> {
  return {
    timeline: 0,
    character: 0,
    world: 0,
    foreshadow: 0,
    conflicts: 0,
  }
}

function buildDrafts(changeSet: MemoryChangeSet | null): Record<MemoryChangeType, string> {
  if (!changeSet) return emptyDrafts()
  return {
    timeline: stringifyJson(getChanges(changeSet, 'timeline')),
    character: stringifyJson(getChanges(changeSet, 'character')),
    world: stringifyJson(getChanges(changeSet, 'world')),
    foreshadow: stringifyJson(getChanges(changeSet, 'foreshadow')),
    conflicts: stringifyJson(getChanges(changeSet, 'conflicts')),
  }
}

function getChanges(changeSet: MemoryChangeSet, type: MemoryChangeType): MemoryChange[] {
  const fromChanges = changeSet.changes?.[type]
  if (Array.isArray(fromChanges)) return fromChanges
  if (type === 'timeline') return changeSet.timelineChanges ?? changeSet.timeline_changes ?? []
  if (type === 'character') return changeSet.characterChanges ?? changeSet.character_changes ?? []
  if (type === 'world') return changeSet.worldChanges ?? changeSet.world_changes ?? []
  if (type === 'foreshadow') return changeSet.foreshadowChanges ?? changeSet.foreshadow_changes ?? []
  return changeSet.conflicts ?? []
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
  const conflicts = parseJsonArray(drafts.conflicts, 'conflicts')
  if (!conflicts.ok) return conflicts
  return {
    ok: true,
    value: {
      timeline: timeline.value,
      character: character.value,
      world: world.value,
      foreshadow: foreshadow.value,
      conflicts: conflicts.value,
    },
  }
}

function validateDrafts(drafts: Record<MemoryChangeType, string>):
  Record<MemoryChangeType, { ok: true; count: number } | { ok: false; message: string }> {
  return CHANGE_TYPES.reduce<Record<MemoryChangeType, { ok: true; count: number } | { ok: false; message: string }>>(
    (acc, item) => {
      const parsed = parseJsonArray(drafts[item.key], item.key)
      acc[item.key] = parsed.ok ? { ok: true, count: parsed.value.length } : parsed
      return acc
    },
    {
      timeline: { ok: true, count: 0 },
      character: { ok: true, count: 0 },
      world: { ok: true, count: 0 },
      foreshadow: { ok: true, count: 0 },
      conflicts: { ok: true, count: 0 },
    },
  )
}

function buildUpdateRequest(parsed: Record<MemoryChangeType, MemoryChange[]>) {
  return {
    timelineChanges: parsed.timeline,
    timeline_changes: parsed.timeline,
    characterChanges: parsed.character,
    character_changes: parsed.character,
    worldChanges: parsed.world,
    world_changes: parsed.world,
    foreshadowChanges: parsed.foreshadow,
    foreshadow_changes: parsed.foreshadow,
    conflicts: parsed.conflicts,
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

function nextActionMessage(stage: string, hasUnsavedDrafts: boolean, allDraftsValid: boolean) {
  if (stage === 'chapter_confirmed') return 'Chapter is frozen. Memory editing and confirmation are locked.'
  if (stage === 'memory_confirmed') return 'Memory is confirmed. Freeze the chapter when the final lock is intentional.'
  if (!allDraftsValid) return 'Fix invalid JSON arrays before saving or confirming memory.'
  if (hasUnsavedDrafts) return 'Confirm will save your valid edits first, then mark memory as confirmed.'
  return 'Confirm memory after reviewing all categories. Freeze becomes available after confirmation.'
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
