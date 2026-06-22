import assert from 'node:assert/strict'
import { readdir, readFile } from 'node:fs/promises'
import { dirname, extname, relative, resolve } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const currentDir = dirname(fileURLToPath(import.meta.url))
const frontendRoot = resolve(currentDir, '../..')
const srcRoot = resolve(frontendRoot, 'src')
const packageJson = JSON.parse(await readFile(resolve(frontendRoot, 'package.json'), 'utf8'))

const sourceFiles = (await listSourceFiles(srcRoot)).filter((filePath) => !filePath.includes('.test.'))
const sources = Object.fromEntries(
  await Promise.all(sourceFiles.map(async (filePath) => [
    toProjectPath(filePath),
    await readFile(filePath, 'utf8'),
  ])),
)

const appSource = sources['src/App.tsx']
const apiSource = sources['src/services/api.ts']
const sseHookSource = sources['src/hooks/useSSE.ts']
const creationConsoleSource = sources['src/components/CreationConsole.tsx']
const livePreviewSource = sources['src/components/LivePreview.tsx']
const outlineOptionsSource = sources['src/components/OutlineOptionsPanel.tsx']
const memoryChangeSetSource = sources['src/components/MemoryChangeSetPanel.tsx']

test('workbench acceptance test is wired as an npm script', () => {
  assert.equal(
    packageJson.scripts?.['test:workbench'],
    'node --test src/services/workbench-flow.test.mjs',
  )
})

test('App mounts the full workbench flow in the accepted left-center-right order', () => {
  assertInOrder(appSource, [
    '<NovelIdeaChat',
    '<CreationConsole',
    '<LivePreview',
    '<AgentStatus',
    '<GenerationHistory',
    '<OutlineOptionsPanel',
    '<MemoryChangeSetPanel',
  ])

  assert.match(appSource, /className="workspace-sidebar"/)
  assert.match(appSource, /className="workspace-editor"/)
  assert.match(appSource, /className="workspace-rail"/)
})

test('frontend source never bypasses the Java boundary for AI/internal routes', () => {
  const forbidden = [
    /\/internal\/ai/,
    /localhost:8000/,
    /PYTHON_AI_BASE_URL/,
    /python-ai/i,
  ]

  for (const [filePath, source] of Object.entries(sources)) {
    for (const pattern of forbidden) {
      assert.doesNotMatch(source, pattern, `${filePath} must not match ${pattern}`)
    }
  }
})

test('P6 gate: next chapter requires the previous chapter to be approved or confirmed', () => {
  assert.match(creationConsoleSource, /Next chapter/)
  assert.match(creationConsoleSource, /canContinueToNextChapter/)
  assert.match(creationConsoleSource, /isChapterContinuationUnlocked/)
  assert.match(creationConsoleSource, /workflowStage === 'chapter_confirmed'/)
  assert.match(creationConsoleSource, /workflowStage === 'approved'/)
  assert.match(creationConsoleSource, /status === 'approved'/)
})

test('P6 gate: confirmed outlines stay folded through later chapter stages', () => {
  assert.match(outlineOptionsSource, /isOutlineConfirmedStage/)
  assertStageLiterals(outlineOptionsSource, [
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
  ])
})

test('P6 gate: draft confirmation is blocked on P0/blocking issues and tracks adoption identity', () => {
  assert.match(livePreviewSource, /getConfirmationReadiness/)
  assert.match(livePreviewSource, /blockingCount > 0/)
  assert.match(livePreviewSource, /severity === 'P0'/)
  assert.match(livePreviewSource, /generation\?\.adopted/)
  assert.match(livePreviewSource, /last_generation_id/)
  assert.match(appSource, /confirmChapterGeneration/)
  assert.match(appSource, /setDraftConfirming\(true\)/)
})

test('P6 gate: memory confirmation covers conflicts, valid JSON, and final freeze', () => {
  assert.match(memoryChangeSetSource, /key: 'conflicts'/)
  assert.match(memoryChangeSetSource, /conflicts: parsed\.conflicts/)
  assert.match(memoryChangeSetSource, /parseJsonArray/)
  assert.match(memoryChangeSetSource, /Valid JSON array/)
  assert.match(memoryChangeSetSource, /allDraftsValid/)
  assert.match(memoryChangeSetSource, /freezeMemoryChangeSet/)
  assert.match(memoryChangeSetSource, /Freeze chapter/)
  assert.match(memoryChangeSetSource, /FINAL_STAGES = \['chapter_confirmed'\]/)
})

test('SSE event stream is created only through Java generation events', () => {
  const eventSourceUsers = Object.entries(sources)
    .filter(([, source]) => /\bEventSource\s*\(/.test(source))
    .map(([filePath]) => filePath)

  assert.deepEqual(eventSourceUsers, ['src/services/api.ts'])
  assert.match(sseHookSource, /generateChapterStream/)
  assert.match(apiSource, /createChapterGeneration\(req\)/)
  assert.match(
    apiSource,
    /\/api\/stories\/\$\{req\.story_id\}\/chapters\/\$\{req\.chapter_id\}\/generations\/\$\{generation\.id\}\/events/,
  )
  assert.doesNotMatch(apiSource, /\/events\s*\?/)
})

function assertInOrder(source, needles) {
  let lastIndex = -1
  for (const needle of needles) {
    const index = source.indexOf(needle)
    assert.notEqual(index, -1, `Expected to find ${needle}`)
    assert.ok(index > lastIndex, `Expected ${needle} to appear after prior workbench section`)
    lastIndex = index
  }
}

function assertStageLiterals(source, stages) {
  for (const stage of stages) {
    assert.match(source, new RegExp(`'${stage}'`))
  }
}

async function listSourceFiles(dir) {
  const entries = await readdir(dir, { withFileTypes: true })
  const files = await Promise.all(entries.map(async (entry) => {
    const entryPath = resolve(dir, entry.name)
    if (entry.isDirectory()) return listSourceFiles(entryPath)
    return isSourceFile(entryPath) ? [entryPath] : []
  }))
  return files.flat()
}

function isSourceFile(filePath) {
  return ['.ts', '.tsx', '.js', '.jsx', '.mjs'].includes(extname(filePath))
}

function toProjectPath(filePath) {
  return relative(frontendRoot, filePath).replaceAll('\\', '/')
}
