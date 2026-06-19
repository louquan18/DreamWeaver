import { useMemo, useState, type FormEvent } from 'react'
import {
  confirmNovelBlueprint,
  createStory,
  generateNovelBlueprint,
  updateNovelBlueprint,
} from '../services/api'
import type { BlueprintGenerateResult, BlueprintUpdateRequest, NovelBlueprint, Story } from '../types'
import './NovelIdeaChat.css'

const SAMPLE_IDEAS = [
  'A fallen cultivator runs a bookstore that secretly archives forbidden prophecies.',
  'A cyberpunk detective discovers every unsolved case is a discarded chapter from one novel.',
]

interface NovelIdeaChatProps {
  onStoryCreated?: (story: Story) => void
}

interface BlueprintFormState {
  sourcePrompt: string
  premise: string
  genre: string
  tone: string
  protagonistName: string
  protagonistIdentity: string
  protagonistInitialGoal: string
  protagonistMotivation: string
  protagonistTraits: string
  mainThreadGoal: string
  mainThreadObstacle: string
  coreConflictExternal: string
  coreConflictInternal: string
  coreConflictStakes: string
  worldSetting: string
  worldRules: string
  worldAesthetic: string
  writingPace: string
  writingStyle: string
  writingAvoid: string
  lockedFacts: string
}

export function NovelIdeaChat({ onStoryCreated }: NovelIdeaChatProps) {
  const [idea, setIdea] = useState('')
  const [result, setResult] = useState<BlueprintGenerateResult | null>(null)
  const [form, setForm] = useState<BlueprintFormState>(() => emptyBlueprintForm())
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [confirming, setConfirming] = useState(false)

  const trimmedIdea = idea.trim()
  const characterCount = trimmedIdea.length
  const busy = loading || saving || confirming
  const activeBlueprint = result?.blueprint
  const activeStoryId = result?.story?.id || activeBlueprint?.storyId || activeBlueprint?.story_id || ''
  const activeBlueprintId = activeBlueprint?.id || ''
  const blueprintStatus = activeBlueprint?.status || 'generated'
  const isConfirmed = blueprintStatus.toLowerCase() === 'confirmed'
  const canEdit = Boolean(activeStoryId && activeBlueprintId && !isConfirmed)
  const canConfirm = canEdit && isConfirmReady(form)

  const summary = useMemo(() => {
    if (!activeBlueprint) return null
    return buildBlueprintSummary(activeBlueprint)
  }, [activeBlueprint])

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    if (!trimmedIdea || busy) return

    setLoading(true)
    setError('')
    setNotice('')
    setResult(null)
    try {
      const story = await createStory({
        title: buildStoryTitle(trimmedIdea),
        description: trimmedIdea,
      })
      onStoryCreated?.(story)

      const data = await generateNovelBlueprint(story.id, {
        sourcePrompt: trimmedIdea,
      })
      const nextResult = {
        ...data,
        story: data.story ?? story,
      }
      setResult(nextResult)
      setForm(buildBlueprintForm(nextResult.blueprint))
      setNotice('Blueprint draft ready. Review, edit, then save or confirm it.')
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to generate blueprint')
    } finally {
      setLoading(false)
    }
  }

  async function handleSaveBlueprint() {
    if (!activeBlueprint || !activeStoryId || !activeBlueprintId || saving || confirming) return

    setSaving(true)
    setError('')
    setNotice('')
    try {
      const editedBlueprint = buildBlueprintUpdate(form, activeBlueprint)
      const blueprint = await updateNovelBlueprint(activeStoryId, activeBlueprintId, editedBlueprint)
      setResult((current) => current && {
        ...current,
        blueprint,
      })
      setForm(buildBlueprintForm(blueprint))
      setNotice('Blueprint edits saved.')
    } catch (saveError) {
      setError(saveError instanceof Error ? saveError.message : 'Failed to save blueprint edits')
    } finally {
      setSaving(false)
    }
  }

  async function handleConfirmBlueprint() {
    if (!activeBlueprint || !activeStoryId || !activeBlueprintId || saving || confirming) return

    setConfirming(true)
    setError('')
    setNotice('')
    try {
      const confirmed = await confirmNovelBlueprint(activeStoryId, activeBlueprintId, {
        editedBlueprint: buildBlueprintUpdate(form, activeBlueprint),
      })
      setResult((current) => current && {
        ...current,
        story: confirmed.story ?? current.story,
        blueprint: confirmed.blueprint,
      })
      setForm(buildBlueprintForm(confirmed.blueprint))
      if (confirmed.story) {
        onStoryCreated?.(confirmed.story)
      }
      setNotice('Blueprint confirmed. This novel is ready for chapter planning.')
    } catch (confirmError) {
      setError(confirmError instanceof Error ? confirmError.message : 'Failed to confirm blueprint')
    } finally {
      setConfirming(false)
    }
  }

  function handleSample(sample: string) {
    if (busy) return
    setIdea(sample)
    setError('')
    setNotice('')
  }

  function updateFormField(field: keyof BlueprintFormState, value: string) {
    setForm((current) => ({
      ...current,
      [field]: value,
    }))
    setNotice('')
  }

  return (
    <section className="idea-chat" aria-labelledby="idea-chat-title">
      <div className="idea-chat-header">
        <div>
          <p className="idea-chat-kicker">Novel kickoff</p>
          <h2 id="idea-chat-title">Start from one idea</h2>
        </div>
        <span className={`idea-chat-state ${busy ? 'loading' : result ? 'success' : 'idle'}`}>
          {loading ? 'Generating' : saving ? 'Saving' : confirming ? 'Confirming' : result ? 'Blueprint ready' : 'Drafting room'}
        </span>
      </div>

      <form className="idea-chat-form" onSubmit={handleSubmit}>
        <label htmlFor="novel-idea">Tell DreamWeaver the novel you want to write.</label>
        <textarea
          id="novel-idea"
          value={idea}
          onChange={(event) => setIdea(event.target.value)}
          placeholder="Example: A young archivist inherits a haunted starship and must rewrite its logbook before the crew repeats a century-old mutiny."
          rows={5}
          maxLength={10000}
          disabled={busy}
        />

        <div className="idea-chat-tools">
          <span>{characterCount.toLocaleString()} / 10,000</span>
          <button type="submit" disabled={!trimmedIdea || busy}>
            {loading ? 'Building blueprint...' : 'Generate blueprint'}
          </button>
        </div>
      </form>

      {!result && (
        <div className="idea-samples" aria-label="Sample ideas">
          {SAMPLE_IDEAS.map((sample) => (
            <button key={sample} type="button" onClick={() => handleSample(sample)} disabled={busy}>
              {sample}
            </button>
          ))}
        </div>
      )}

      {loading && (
        <div className="idea-chat-loading" role="status">
          <span />
          <div>
            <strong>Calling the blueprint agent</strong>
            <p>Expanding premise, protagonist, conflict, world seed, and locked facts.</p>
          </div>
        </div>
      )}

      {error && <div className="idea-chat-message error">{error}</div>}
      {notice && <div className="idea-chat-message success">{notice}</div>}

      {result && summary && (
        <div className="blueprint-summary">
          <div className="summary-head">
            <div>
              <span>{result.story?.title || summary.genreTone || 'Generated blueprint'}</span>
              <h3>{summary.premise}</h3>
            </div>
            <strong>{blueprintStatus}</strong>
          </div>

          <div className="blueprint-form" aria-label="Editable blueprint form">
            <label className="field-wide">
              <span>Source prompt</span>
              <textarea
                value={form.sourcePrompt}
                onChange={(event) => updateFormField('sourcePrompt', event.target.value)}
                rows={3}
                disabled={!canEdit || busy}
              />
            </label>

            <label className="field-wide">
              <span>Premise</span>
              <textarea
                value={form.premise}
                onChange={(event) => updateFormField('premise', event.target.value)}
                rows={3}
                maxLength={2000}
                disabled={!canEdit || busy}
              />
            </label>

            <label>
              <span>Genre</span>
              <input
                type="text"
                value={form.genre}
                onChange={(event) => updateFormField('genre', event.target.value)}
                maxLength={50}
                disabled={!canEdit || busy}
              />
            </label>

            <label>
              <span>Tone</span>
              <input
                type="text"
                value={form.tone}
                onChange={(event) => updateFormField('tone', event.target.value)}
                maxLength={100}
                disabled={!canEdit || busy}
              />
            </label>

            <div className="blueprint-group field-wide">
              <div className="blueprint-group-title">Protagonist</div>
              <div className="blueprint-form nested">
                <label>
                  <span>Name</span>
                  <input
                    type="text"
                    value={form.protagonistName}
                    onChange={(event) => updateFormField('protagonistName', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Identity</span>
                  <input
                    type="text"
                    value={form.protagonistIdentity}
                    onChange={(event) => updateFormField('protagonistIdentity', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Initial goal</span>
                  <input
                    type="text"
                    value={form.protagonistInitialGoal}
                    onChange={(event) => updateFormField('protagonistInitialGoal', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Motivation</span>
                  <input
                    type="text"
                    value={form.protagonistMotivation}
                    onChange={(event) => updateFormField('protagonistMotivation', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label className="field-wide">
                  <span>Traits</span>
                  <input
                    type="text"
                    value={form.protagonistTraits}
                    onChange={(event) => updateFormField('protagonistTraits', event.target.value)}
                    placeholder="Comma-separated traits"
                    disabled={!canEdit || busy}
                  />
                </label>
              </div>
            </div>

            <div className="blueprint-group field-wide">
              <div className="blueprint-group-title">Story engine</div>
              <div className="blueprint-form nested">
                <label>
                  <span>Main goal</span>
                  <input
                    type="text"
                    value={form.mainThreadGoal}
                    onChange={(event) => updateFormField('mainThreadGoal', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Obstacle</span>
                  <input
                    type="text"
                    value={form.mainThreadObstacle}
                    onChange={(event) => updateFormField('mainThreadObstacle', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>External conflict</span>
                  <input
                    type="text"
                    value={form.coreConflictExternal}
                    onChange={(event) => updateFormField('coreConflictExternal', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Internal conflict</span>
                  <input
                    type="text"
                    value={form.coreConflictInternal}
                    onChange={(event) => updateFormField('coreConflictInternal', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label className="field-wide">
                  <span>Stakes</span>
                  <input
                    type="text"
                    value={form.coreConflictStakes}
                    onChange={(event) => updateFormField('coreConflictStakes', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
              </div>
            </div>

            <div className="blueprint-group field-wide">
              <div className="blueprint-group-title">World and writing rules</div>
              <div className="blueprint-form nested">
                <label>
                  <span>Setting</span>
                  <input
                    type="text"
                    value={form.worldSetting}
                    onChange={(event) => updateFormField('worldSetting', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Aesthetic</span>
                  <input
                    type="text"
                    value={form.worldAesthetic}
                    onChange={(event) => updateFormField('worldAesthetic', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Pace</span>
                  <input
                    type="text"
                    value={form.writingPace}
                    onChange={(event) => updateFormField('writingPace', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label>
                  <span>Style</span>
                  <input
                    type="text"
                    value={form.writingStyle}
                    onChange={(event) => updateFormField('writingStyle', event.target.value)}
                    disabled={!canEdit || busy}
                  />
                </label>
                <label className="field-wide">
                  <span>World rules</span>
                  <textarea
                    value={form.worldRules}
                    onChange={(event) => updateFormField('worldRules', event.target.value)}
                    rows={4}
                    placeholder="One rule per line"
                    disabled={!canEdit || busy}
                  />
                </label>
                <label className="field-wide">
                  <span>Avoid</span>
                  <textarea
                    value={form.writingAvoid}
                    onChange={(event) => updateFormField('writingAvoid', event.target.value)}
                    rows={3}
                    placeholder="One writing constraint per line"
                    disabled={!canEdit || busy}
                  />
                </label>
              </div>
            </div>

            <label className="field-wide">
              <span>Locked facts</span>
              <textarea
                value={form.lockedFacts}
                onChange={(event) => updateFormField('lockedFacts', event.target.value)}
                rows={5}
                placeholder="One hard continuity fact per line"
                disabled={!canEdit || busy}
              />
            </label>
          </div>

          {summary.validationIssues.length > 0 && (
            <div className="blueprint-issues">
              <span>Validation notes</span>
              {summary.validationIssues.map((issue) => (
                <p key={`${issue.path}-${issue.message}`}>{issue.path}: {issue.message}</p>
              ))}
            </div>
          )}

          <div className="blueprint-next">
            <div>
              <button type="button" onClick={handleSaveBlueprint} disabled={!canEdit || busy}>
                {saving ? 'Saving edits...' : 'Save edits'}
              </button>
              <button type="button" className="confirm" onClick={handleConfirmBlueprint} disabled={!canConfirm || busy}>
                {confirming ? 'Confirming...' : 'Confirm blueprint'}
              </button>
            </div>
            <p>
              {isConfirmed
                ? 'Blueprint confirmed.'
                : canConfirm
                  ? 'Required fields are ready.'
                  : 'Premise, lead name, main goal, conflict, and locked facts are needed.'}
            </p>
          </div>
        </div>
      )}
    </section>
  )
}

function buildStoryTitle(idea: string) {
  const normalized = idea.replace(/\s+/g, ' ').trim()
  if (normalized.length <= 48) return normalized
  return `${normalized.slice(0, 47)}...`
}

function emptyBlueprintForm(): BlueprintFormState {
  return {
    sourcePrompt: '',
    premise: '',
    genre: '',
    tone: '',
    protagonistName: '',
    protagonistIdentity: '',
    protagonistInitialGoal: '',
    protagonistMotivation: '',
    protagonistTraits: '',
    mainThreadGoal: '',
    mainThreadObstacle: '',
    coreConflictExternal: '',
    coreConflictInternal: '',
    coreConflictStakes: '',
    worldSetting: '',
    worldRules: '',
    worldAesthetic: '',
    writingPace: '',
    writingStyle: '',
    writingAvoid: '',
    lockedFacts: '',
  }
}

function buildBlueprintForm(blueprint: NovelBlueprint): BlueprintFormState {
  const protagonist = readRecord(blueprint.protagonist)
  const mainThread = readRecord(blueprint.mainThread ?? blueprint.main_thread)
  const coreConflict = readRecord(blueprint.coreConflict ?? blueprint.core_conflict)
  const worldSeed = readRecord(blueprint.worldSeed ?? blueprint.world_seed)
  const writingPreferences = readRecord(blueprint.writingPreferences ?? blueprint.writing_preferences)

  return {
    sourcePrompt: text(blueprint.sourcePrompt ?? blueprint.source_prompt),
    premise: text(blueprint.premise),
    genre: text(blueprint.genre),
    tone: text(blueprint.tone),
    protagonistName: text(protagonist.name),
    protagonistIdentity: text(protagonist.identity),
    protagonistInitialGoal: text(protagonist.initialGoal ?? protagonist.initial_goal),
    protagonistMotivation: text(protagonist.motivation),
    protagonistTraits: listFieldText(protagonist.traits, ', '),
    mainThreadGoal: text(mainThread.goal),
    mainThreadObstacle: text(mainThread.antagonistOrObstacle ?? mainThread.antagonist_or_obstacle),
    coreConflictExternal: text(coreConflict.external),
    coreConflictInternal: text(coreConflict.internal),
    coreConflictStakes: text(coreConflict.stakes),
    worldSetting: text(worldSeed.setting),
    worldRules: listFieldText(worldSeed.rules, '\n'),
    worldAesthetic: text(worldSeed.aesthetic),
    writingPace: text(writingPreferences.pace),
    writingStyle: text(writingPreferences.style),
    writingAvoid: listFieldText(writingPreferences.avoid, '\n'),
    lockedFacts: listFieldText(blueprint.lockedFacts ?? blueprint.locked_facts, '\n'),
  }
}

function buildBlueprintUpdate(form: BlueprintFormState, blueprint: NovelBlueprint): BlueprintUpdateRequest {
  const protagonist = readRecord(blueprint.protagonist)
  const mainThread = readRecord(blueprint.mainThread ?? blueprint.main_thread)
  const coreConflict = readRecord(blueprint.coreConflict ?? blueprint.core_conflict)
  const worldSeed = readRecord(blueprint.worldSeed ?? blueprint.world_seed)
  const writingPreferences = readRecord(blueprint.writingPreferences ?? blueprint.writing_preferences)

  return {
    sourcePrompt: form.sourcePrompt.trim(),
    premise: form.premise.trim(),
    genre: form.genre.trim(),
    tone: form.tone.trim(),
    protagonist: {
      ...protagonist,
      name: form.protagonistName.trim(),
      identity: form.protagonistIdentity.trim(),
      initialGoal: form.protagonistInitialGoal.trim(),
      motivation: form.protagonistMotivation.trim(),
      traits: splitCommaValues(form.protagonistTraits),
    },
    mainThread: {
      ...mainThread,
      goal: form.mainThreadGoal.trim(),
      antagonistOrObstacle: form.mainThreadObstacle.trim(),
    },
    coreConflict: {
      ...coreConflict,
      external: form.coreConflictExternal.trim(),
      internal: form.coreConflictInternal.trim(),
      stakes: form.coreConflictStakes.trim(),
    },
    worldSeed: {
      ...worldSeed,
      setting: form.worldSetting.trim(),
      aesthetic: form.worldAesthetic.trim(),
      rules: mergeRuleLines(form.worldRules, worldSeed.rules),
    },
    writingPreferences: {
      ...writingPreferences,
      pace: form.writingPace.trim(),
      style: form.writingStyle.trim(),
      avoid: splitLineValues(form.writingAvoid),
    },
    lockedFacts: mergeLockedFactLines(form.lockedFacts, blueprint.lockedFacts ?? blueprint.locked_facts),
  }
}

function isConfirmReady(form: BlueprintFormState) {
  return Boolean(
    form.premise.trim()
      && form.protagonistName.trim()
      && form.mainThreadGoal.trim()
      && (form.coreConflictExternal.trim() || form.coreConflictInternal.trim())
      && splitLineValues(form.lockedFacts).length > 0,
  )
}

function buildBlueprintSummary(blueprint: NovelBlueprint) {
  const protagonist = readRecord(blueprint.protagonist)
  const mainThread = readRecord(blueprint.mainThread ?? blueprint.main_thread)
  const coreConflict = readRecord(blueprint.coreConflict ?? blueprint.core_conflict)
  const worldSeed = readRecord(blueprint.worldSeed ?? blueprint.world_seed)
  const lockedFacts = blueprint.lockedFacts ?? blueprint.locked_facts ?? []
  const validationIssues = blueprint.validationIssues ?? blueprint.validation_issues ?? []

  return {
    premise: text(blueprint.premise, 'No premise returned yet.'),
    genreTone: [blueprint.genre, blueprint.tone].filter(Boolean).join(' / '),
    protagonist: pickText(protagonist, ['name', 'initialGoal', 'goal'], 'Lead details pending'),
    mainThread: pickText(mainThread, ['goal', 'arc', 'promise'], 'Main thread pending'),
    conflict: pickText(coreConflict, ['external', 'internal', 'stakes'], 'Conflict pending'),
    worldSeed: pickText(worldSeed, ['setting', 'rules', 'aesthetic'], 'World seed pending'),
    lockedFacts: lockedFacts.map((fact) => text(fact)).filter(Boolean),
    validationIssues,
  }
}

function mergeRuleLines(value: string, original: unknown) {
  const originals = Array.isArray(original) ? original : []
  return splitLineValues(value).map((line, index) => {
    const existing = readRecord(originals[index])
    if (Object.keys(existing).length === 0) return line
    return {
      ...existing,
      description: line,
      locked: existing.locked ?? true,
    }
  })
}

function mergeLockedFactLines(value: string, original: unknown) {
  const originals = Array.isArray(original) ? original : []
  return splitLineValues(value).map((line, index) => ({
    ...readRecord(originals[index]),
    text: line,
  }))
}

function splitLineValues(value: string) {
  return value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

function splitCommaValues(value: string) {
  return value
    .split(',')
    .map((line) => line.trim())
    .filter(Boolean)
}

function listFieldText(value: unknown, separator: string): string {
  if (!Array.isArray(value)) return text(value)
  return value.map((item) => text(item)).filter(Boolean).join(separator)
}

function readRecord(value: unknown): Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value) ? value as Record<string, unknown> : {}
}

function pickText(record: Record<string, unknown>, keys: string[], fallback: string) {
  for (const key of keys) {
    const value = text(record[key])
    if (value) return value
  }
  return fallback
}

function text(value: unknown, fallback = ''): string {
  if (typeof value === 'string') return value.trim() || fallback
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) {
    return value.map((item) => text(item)).filter(Boolean).join(', ') || fallback
  }
  if (typeof value === 'object' && value !== null) {
    const record = value as Record<string, unknown>
    return text(record.text)
      || text(record.description)
      || text(record.name)
      || fallback
  }
  return fallback
}
