import { useCallback, useEffect, useMemo, useState } from 'react'
import {
  confirmChapterOutline,
  generateChapterOutlineOptions,
  listChapterOutlineOptions,
} from '../services/api'
import type { Chapter, ChapterOutlineOption, OutlineOptionCode, OutlineOptionType } from '../types'
import './OutlineOptionsPanel.css'

interface OutlineOptionsPanelProps {
  storyId?: string
  chapterId?: string
  chapter?: Chapter
  refreshKey?: number
  onChapterConfirmed?: (chapter: Chapter) => void
}

const OPTION_ORDER: OutlineOptionCode[] = ['A', 'B', 'C']

const OPTION_COPY: Record<OutlineOptionCode, { title: string; detail: string; signal: string }> = {
  A: {
    title: 'Steady route',
    detail: 'Stable progression',
    signal: 'continuity',
  },
  B: {
    title: 'Pressure route',
    detail: 'Sharper conflict',
    signal: 'stakes',
  },
  C: {
    title: 'Echo route',
    detail: 'Foreshadow payoff',
    signal: 'payoff',
  },
}

export function OutlineOptionsPanel({
  storyId,
  chapterId,
  chapter,
  refreshKey = 0,
  onChapterConfirmed,
}: OutlineOptionsPanelProps) {
  const [options, setOptions] = useState<ChapterOutlineOption[]>([])
  const [loading, setLoading] = useState(false)
  const [generating, setGenerating] = useState(false)
  const [confirming, setConfirming] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [primaryOptionId, setPrimaryOptionId] = useState('')
  const [selectedOptionIds, setSelectedOptionIds] = useState<string[]>([])
  const [userFeedback, setUserFeedback] = useState('')
  const [detailsOpen, setDetailsOpen] = useState(false)

  const canLoad = Boolean(storyId && chapterId)
  const workflowStage = normalizeStage(chapter?.workflowStage ?? chapter?.workflow_stage)
  const outlineConfirmed = isOutlineConfirmedStage(workflowStage)

  const loadOptions = useCallback(async () => {
    if (!storyId || !chapterId) {
      setOptions([])
      setError('')
      setNotice('')
      setPrimaryOptionId('')
      setSelectedOptionIds([])
      return
    }

    setLoading(true)
    setError('')
    setNotice('')
    try {
      const data = await listChapterOutlineOptions(storyId, chapterId)
      const sorted = sortOptions(data)
      const availableIds = new Set(sorted.map((option) => option.id).filter(Boolean))
      const firstId = sorted.find((option) => Boolean(option.id))?.id || ''

      setOptions(sorted)
      setPrimaryOptionId((current) => availableIds.has(current) ? current : firstId)
      setSelectedOptionIds((current) => {
        const retained = current.filter((id) => availableIds.has(id))
        if (retained.length > 0) return retained
        return firstId ? [firstId] : []
      })
    } catch (loadError) {
      setOptions([])
      setError(loadError instanceof Error ? loadError.message : 'Failed to load outline options')
    } finally {
      setLoading(false)
    }
  }, [chapterId, storyId])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    void loadOptions()
  }, [loadOptions, refreshKey])

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setDetailsOpen(false)
  }, [chapterId, outlineConfirmed])

  const grouped = useMemo(() => sortOptions(options), [options])
  const selectedIdSet = useMemo(() => new Set(selectedOptionIds), [selectedOptionIds])
  const busy = loading || generating || confirming
  const primaryOption = useMemo(
    () => grouped.find((option) => option.id === primaryOptionId),
    [grouped, primaryOptionId],
  )
  const selectedOptions = useMemo(
    () => grouped.filter((option) => Boolean(option.id && selectedIdSet.has(option.id))),
    [grouped, selectedIdSet],
  )
  const mixedOptions = useMemo(
    () => selectedOptions.filter((option) => option.id !== primaryOptionId),
    [primaryOptionId, selectedOptions],
  )
  const sourceOptions = useMemo(() => {
    if (!primaryOption || selectedOptions.some((option) => option.id === primaryOption.id)) {
      return selectedOptions
    }
    return [primaryOption, ...selectedOptions]
  }, [primaryOption, selectedOptions])
  const canConfirm = Boolean(storyId && chapterId && primaryOption?.id && isOptionConfirmable(primaryOption))
  const showDetails = !outlineConfirmed || detailsOpen
  const primaryLabel = primaryOption ? `Option ${optionCode(primaryOption)}` : 'None'
  const sourceLabels = sourceOptions.map((option) => `Option ${optionCode(option)}`)

  async function handleGenerateOptions() {
    if (!storyId || !chapterId || generating) return

    setGenerating(true)
    setError('')
    setNotice('')
    try {
      const result = await generateChapterOutlineOptions(storyId, chapterId)
      const sorted = sortOptions(result.options)
      const firstId = sorted.find((option) => Boolean(option.id))?.id || ''
      setOptions(sorted)
      setPrimaryOptionId(firstId)
      setSelectedOptionIds(firstId ? [firstId] : [])
      setNotice('Outline options generated. Pick a route and confirm the final outline.')
      onChapterConfirmed?.(result.chapter)
    } catch (generateError) {
      setOptions([])
      setError(generateError instanceof Error ? generateError.message : 'Failed to generate outline options')
    } finally {
      setGenerating(false)
    }
  }

  async function handleConfirmOutline() {
    if (!storyId || !chapterId || !primaryOption?.id || confirming) return

    setConfirming(true)
    setError('')
    setNotice('')
    try {
      const sourceOptionIds = selectedOptionIds.includes(primaryOption.id)
        ? selectedOptionIds
        : [primaryOption.id, ...selectedOptionIds]
      const result = await confirmChapterOutline(storyId, chapterId, {
        sourceOptionIds,
        userFeedback: userFeedback.trim() || undefined,
        finalOutline: buildFinalOutline(primaryOption),
      })
      setNotice('Outline confirmed. Draft generation is now unlocked for this chapter.')
      setDetailsOpen(false)
      onChapterConfirmed?.(result.chapter)
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : 'Failed to confirm chapter outline')
    } finally {
      setConfirming(false)
    }
  }

  function handleSelectPrimary(option: ChapterOutlineOption) {
    const optionId = option.id
    if (!optionId || confirming) return
    setPrimaryOptionId(optionId)
    setSelectedOptionIds((current) => current.includes(optionId) ? current : [...current, optionId])
    setNotice('')
  }

  function handleToggleSource(option: ChapterOutlineOption) {
    const optionId = option.id
    if (!optionId || confirming) return
    setSelectedOptionIds((current) => {
      if (current.includes(optionId)) {
        return optionId === primaryOptionId ? current : current.filter((id) => id !== optionId)
      }
      return [...current, optionId]
    })
    setNotice('')
  }

  return (
    <section className="outline-panel" aria-label="Chapter outline options">
      <div className="outline-panel-header">
        <div>
          <span className="outline-kicker">Outline board</span>
          <h2>A/B/C chapter routes</h2>
        </div>
        <div className="outline-header-actions">
          {!outlineConfirmed && (
            <button type="button" onClick={handleGenerateOptions} disabled={!canLoad || busy}>
              {generating ? 'Generating' : 'Generate'}
            </button>
          )}
          <button type="button" onClick={loadOptions} disabled={!canLoad || busy}>
            {loading ? 'Loading' : 'Refresh'}
          </button>
        </div>
      </div>

      {!canLoad && (
        <div className="outline-empty">
          Select a novel and chapter to inspect generated outline options.
        </div>
      )}

      {canLoad && error && (
        <div className="outline-empty error">
          {error}
        </div>
      )}

      {canLoad && notice && (
        <div className="outline-empty success">
          {notice}
        </div>
      )}

      {canLoad && !error && grouped.length === 0 && !loading && (
        <div className="outline-empty">
          No A/B/C outline options have been saved for this chapter yet.
        </div>
      )}

      {canLoad && !error && grouped.length > 0 && (
        <>
          {outlineConfirmed && (
            <div className="outline-confirmed-strip">
              <div>
                <span className="outline-kicker">Outline confirmed</span>
                <strong>
                  {primaryOption ? `${primaryLabel} saved as final outline` : 'Final outline saved'}
                </strong>
                <p>
                  Sources: {sourceLabels.length > 0 ? sourceLabels.join(', ') : primaryLabel}. Draft generation can use the confirmed outline.
                </p>
              </div>
              <button type="button" onClick={() => setDetailsOpen((open) => !open)}>
                {detailsOpen ? 'Hide outline' : 'View outline'}
              </button>
            </div>
            )}

          {!outlineConfirmed && (
            <div className="outline-confirm-box">
              <div className="outline-decision-header">
                <div>
                  <span className="outline-kicker">Editor decision</span>
                  <h3>Confirm final outline</h3>
                  <p>
                    The primary route becomes the saved final outline. Mixed sources and direction notes are sent as guidance.
                  </p>
                </div>
                <div className="outline-source-summary" aria-label="Selected outline sources">
                  <span>Primary</span>
                  <strong>{primaryLabel}</strong>
                  <span>Mixed sources</span>
                  <strong>
                    {mixedOptions.length > 0 ? mixedOptions.map((option) => optionCode(option)).join(' + ') : 'None'}
                  </strong>
                </div>
              </div>

              <OutlineComparison options={grouped} primaryOptionId={primaryOptionId} selectedIdSet={selectedIdSet} />

              <div className="outline-source-chips" aria-label="Final outline source selection">
                {grouped.map((option) => {
                  const code = optionCode(option)
                  const active = Boolean(option.id && selectedIdSet.has(option.id))
                  const primary = option.id === primaryOptionId
                  return (
                    <span key={`source-${option.id || code}`} className={active ? 'selected' : ''}>
                      {code}
                      {primary ? ' primary' : active ? ' mixed' : ' available'}
                    </span>
                  )
                })}
              </div>

              <label>
                <span>Final outline direction</span>
                <textarea
                  value={userFeedback}
                  onChange={(event) => {
                    setUserFeedback(event.target.value)
                    setNotice('')
                  }}
                  rows={4}
                  maxLength={2000}
                  placeholder="Example: Save A as the base, borrow B's confrontation pressure, and preserve C's ending hook for the next chapter."
                  disabled={confirming}
                />
              </label>
              <div className="outline-confirm-actions">
                <p>
                  {primaryOption
                    ? `Saving ${primaryLabel} with ${sourceLabels.length} source${sourceLabels.length === 1 ? '' : 's'}: ${sourceLabels.join(', ')}.`
                    : 'Choose a primary option before confirming.'}
                </p>
                <button type="button" onClick={handleConfirmOutline} disabled={!canConfirm || confirming}>
                  {confirming ? 'Confirming...' : 'Confirm outline'}
                </button>
              </div>
            </div>
          )}

          {showDetails && (
            <div className="outline-grid">
              {grouped.map((option) => (
                <OutlineOptionCard
                  key={option.id || option.optionCode}
                  option={option}
                  isPrimary={option.id === primaryOptionId}
                  isSelected={Boolean(option.id && selectedIdSet.has(option.id))}
                  onPrimary={() => handleSelectPrimary(option)}
                  onToggle={() => handleToggleSource(option)}
                  disabled={confirming || outlineConfirmed}
                />
              ))}
            </div>
          )}
        </>
      )}
    </section>
  )
}

function OutlineComparison({
  options,
  primaryOptionId,
  selectedIdSet,
}: {
  options: ChapterOutlineOption[]
  primaryOptionId: string
  selectedIdSet: Set<string>
}) {
  return (
    <div className="outline-comparison" aria-label="A/B/C route comparison">
      <div className="outline-comparison-head">
        <span>Route</span>
        <span>Core move</span>
        <span>Scene shape</span>
        <span>Hook</span>
      </div>
      {options.map((option) => {
        const code = optionCode(option)
        const isPrimary = option.id === primaryOptionId
        const isSelected = Boolean(option.id && selectedIdSet.has(option.id))
        const scenes = option.sceneOutline ?? option.scene_outline ?? []
        const hook = option.endingHook ?? option.ending_hook ?? option.highlightMoment ?? option.highlight_moment
        const goal = option.chapterGoal ?? option.chapter_goal ?? 'No goal returned.'
        return (
          <div
            className={`outline-comparison-row ${isPrimary ? 'primary' : ''} ${isSelected ? 'selected' : ''}`}
            key={`compare-${option.id || code}`}
          >
            <strong>
              {code}
              <span>{OPTION_COPY[code]?.signal || optionType(option)}</span>
            </strong>
            <p>{goal}</p>
            <span>{scenes.length || 0} beats</span>
            <p>{hook || 'No hook returned.'}</p>
          </div>
        )
      })}
    </div>
  )
}

function OutlineOptionCard({
  option,
  isPrimary,
  isSelected,
  onPrimary,
  onToggle,
  disabled,
}: {
  option: ChapterOutlineOption
  isPrimary: boolean
  isSelected: boolean
  onPrimary: () => void
  onToggle: () => void
  disabled: boolean
}) {
  const code = optionCode(option)
  const copy = OPTION_COPY[code] || {
    title: `${code} route`,
    detail: optionType(option),
    signal: optionType(option),
  }
  const scenes = option.sceneOutline ?? option.scene_outline ?? []
  const foreshadowActions = option.foreshadowActions ?? option.foreshadow_actions ?? []
  const memoryReferences = option.memoryReferences ?? option.memory_references ?? []
  const sceneCount = scenes.length
  const foreshadowCount = foreshadowActions.length
  const memoryCount = memoryReferences.length
  const highlightMoment = option.highlightMoment ?? option.highlight_moment
  const endingHook = option.endingHook ?? option.ending_hook
  const whyThisPlan = option.whyThisPlan ?? option.why_this_plan

  return (
    <article className={`outline-card option-${code.toLowerCase()} ${isPrimary ? 'primary' : ''} ${isSelected ? 'selected' : ''}`}>
      <div className="outline-card-top">
        <div className="option-mark" aria-label={`Option ${code}`}>
          {code}
        </div>
        <div>
          <h3>{copy.title}</h3>
          <span>{copy.detail} / {copy.signal}</span>
        </div>
      </div>

      <div className="outline-card-state" aria-label={`Option ${code} selection state`}>
        <span className={isPrimary ? 'primary' : ''}>{isPrimary ? 'Primary base' : 'Alternative'}</span>
        <span className={isSelected ? 'selected' : ''}>{isSelected ? 'Included source' : 'Not mixed'}</span>
      </div>

      <div className="outline-title-row">
        <strong>{firstTitle(option)}</strong>
        <span>{option.status || 'generated'}</span>
      </div>

      <div className="outline-choice-row">
        <button type="button" onClick={onPrimary} disabled={disabled || !option.id} className={isPrimary ? 'active' : ''}>
          {isPrimary ? 'Primary route' : 'Use as primary'}
        </button>
        <label>
          <input
            type="checkbox"
            checked={isSelected}
            onChange={onToggle}
            disabled={disabled || !option.id || isPrimary}
          />
          Mix source
        </label>
      </div>

      <p className="outline-goal">{option.chapterGoal ?? option.chapter_goal ?? 'No chapter goal returned.'}</p>
      <p className="outline-summary">{option.storySummary ?? option.story_summary ?? 'No story summary returned.'}</p>

      <div className="outline-stat-row" aria-label="Outline option metrics">
        <span>{sceneCount} scenes</span>
        <span>{foreshadowCount} foreshadow</span>
        <span>{memoryCount} memory</span>
      </div>

      <div className="outline-scenes">
        {scenes.slice(0, 5).map((scene, index) => (
          <div className="outline-scene" key={`${code}-${scene.order || index}`}>
            <span>{scene.order || index + 1}</span>
            <p>{scene.summary || scene.outcome || 'Untitled beat'}</p>
          </div>
        ))}
      </div>

      {(highlightMoment || endingHook) && (
        <div className="outline-callout">
          {highlightMoment && <p>{highlightMoment}</p>}
          {endingHook && <strong>{endingHook}</strong>}
        </div>
      )}

      {foreshadowActions.length > 0 && (
        <div className="outline-mini-section">
          <span>Foreshadow</span>
          {foreshadowActions.slice(0, 2).map((action, index) => (
            <p key={`${action.foreshadowId || action.foreshadow_id || action.action || 'action'}-${index}`}>
              <strong>{action.action || 'action'}</strong>
              {' '}
              {action.description || action.payoffHint || action.payoff_hint || action.foreshadowId || action.foreshadow_id || 'Unspecified'}
            </p>
          ))}
        </div>
      )}

      <div className="outline-reason">
        <span>Why this plan</span>
        <p>{whyThisPlan || 'No explanation returned.'}</p>
      </div>
    </article>
  )
}

function sortOptions(options: ChapterOutlineOption[]) {
  return [...options].sort((left, right) => {
    const leftIndex = OPTION_ORDER.indexOf(optionCode(left))
    const rightIndex = OPTION_ORDER.indexOf(optionCode(right))
    return normalizeIndex(leftIndex) - normalizeIndex(rightIndex)
  })
}

function normalizeIndex(index: number) {
  return index === -1 ? 99 : index
}

function firstTitle(option: ChapterOutlineOption) {
  return (option.titleCandidates ?? option.title_candidates)?.find(Boolean) || `${typeLabel(optionType(option))} option`
}

function typeLabel(type: OutlineOptionType | string) {
  if (type === 'steady') return 'Steady'
  if (type === 'conflict') return 'Conflict'
  if (type === 'foreshadow') return 'Foreshadow'
  return type
}

function optionCode(option: ChapterOutlineOption): OutlineOptionCode {
  return option.optionCode ?? option.option_code ?? 'A'
}

function optionType(option: ChapterOutlineOption): OutlineOptionType {
  return option.optionType ?? option.option_type ?? 'steady'
}

function isOptionConfirmable(option: ChapterOutlineOption) {
  const finalOutline = buildFinalOutline(option)
  return Boolean(
    Array.isArray(finalOutline.titleCandidates)
      && finalOutline.titleCandidates.length > 0
      && finalOutline.chapterGoal
      && finalOutline.storySummary
      && Array.isArray(finalOutline.sceneOutline)
      && finalOutline.sceneOutline.length >= 3
      && finalOutline.sceneOutline.length <= 5
      && Array.isArray(finalOutline.charactersInvolved)
      && finalOutline.charactersInvolved.length > 0
      && finalOutline.conflict
      && finalOutline.highlightMoment
      && finalOutline.whyThisPlan
      && finalOutline.endingHook,
  )
}

function normalizeStage(value?: string) {
  return (value || '').toLowerCase()
}

function isOutlineConfirmedStage(stage: string) {
  return [
    'outline_confirmed',
    'draft_generating',
    'draft_generated',
    'draft_ready_for_confirmation',
    'reviewing',
    'revision_required',
    'draft_confirmed',
    'memory_extracting',
    'memory_pending_confirmation',
    'memory_confirmed',
    'chapter_confirmed',
  ].includes(stage)
}

function buildFinalOutline(option: ChapterOutlineOption): Record<string, unknown> {
  return {
    titleCandidates: option.titleCandidates ?? option.title_candidates ?? [],
    chapterGoal: option.chapterGoal ?? option.chapter_goal ?? '',
    storySummary: option.storySummary ?? option.story_summary ?? '',
    sceneOutline: option.sceneOutline ?? option.scene_outline ?? [],
    charactersInvolved: option.charactersInvolved ?? option.characters_involved ?? [],
    conflict: option.conflict ?? {},
    highlightMoment: option.highlightMoment ?? option.highlight_moment ?? '',
    foreshadowActions: option.foreshadowActions ?? option.foreshadow_actions ?? [],
    memoryReferences: option.memoryReferences ?? option.memory_references ?? [],
    whyThisPlan: option.whyThisPlan ?? option.why_this_plan ?? '',
    endingHook: option.endingHook ?? option.ending_hook ?? '',
    riskNotes: option.riskNotes ?? option.risk_notes ?? [],
  }
}
