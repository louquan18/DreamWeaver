import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import { dirname, resolve } from 'node:path'
import { test } from 'node:test'
import { fileURLToPath } from 'node:url'

const currentDir = dirname(fileURLToPath(import.meta.url))
const apiSource = await readFile(resolve(currentDir, 'api.ts'), 'utf8')
const ideaChatSource = await readFile(
  resolve(currentDir, '../components/NovelIdeaChat.tsx'),
  'utf8',
)
const outlineOptionsSource = await readFile(
  resolve(currentDir, '../components/OutlineOptionsPanel.tsx'),
  'utf8',
)
const memoryChangeSetPanelSource = await readFile(
  resolve(currentDir, '../components/MemoryChangeSetPanel.tsx'),
  'utf8',
).catch(() => '')
const generationHistorySource = await readFile(
  resolve(currentDir, '../components/GenerationHistory.tsx'),
  'utf8',
)
const sseHookSource = await readFile(resolve(currentDir, '../hooks/useSSE.ts'), 'utf8')
const blueprintSources = `${apiSource}\n${ideaChatSource}`
const outlineSources = `${apiSource}\n${outlineOptionsSource}`
const memorySources = `${apiSource}\n${memoryChangeSetPanelSource}`
const generationSources = `${apiSource}\n${generationHistorySource}\n${sseHookSource}`

test('blueprint API calls stay behind the Java service boundary', () => {
  assert.match(apiSource, /const API_BASE = ''/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/blueprints\/generate/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/blueprints\/\$\{blueprintId\}/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/blueprints\/\$\{blueprintId\}\/confirm/)

  assert.doesNotMatch(blueprintSources, /\/internal\/ai/)
  assert.doesNotMatch(blueprintSources, /localhost:8000/)
  assert.doesNotMatch(blueprintSources, /PYTHON_AI_BASE_URL/)
  assert.doesNotMatch(blueprintSources, /python-ai/i)
})

test('idea kickoff component uses the frontend API client for the blueprint loop', () => {
  assert.match(ideaChatSource, /createStory/)
  assert.match(ideaChatSource, /generateNovelBlueprint/)
  assert.match(ideaChatSource, /updateNovelBlueprint/)
  assert.match(ideaChatSource, /confirmNovelBlueprint/)
  assert.doesNotMatch(ideaChatSource, /\bfetch\s*\(/)
  assert.doesNotMatch(ideaChatSource, /\bEventSource\s*\(/)
})

test('outline option API calls stay behind the Java service boundary', () => {
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/outline-options/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/outline-options\/generate/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/outlines\/confirm/)
  assert.doesNotMatch(outlineSources, /\/internal\/ai/)
  assert.doesNotMatch(outlineSources, /localhost:8000/)
  assert.doesNotMatch(outlineSources, /PYTHON_AI_BASE_URL/)
  assert.doesNotMatch(outlineSources, /python-ai/i)
})

test('outline option component uses the frontend API client', () => {
  assert.match(outlineOptionsSource, /listChapterOutlineOptions/)
  assert.match(outlineOptionsSource, /generateChapterOutlineOptions/)
  assert.match(outlineOptionsSource, /confirmChapterOutline/)
  assert.doesNotMatch(outlineOptionsSource, /\bfetch\s*\(/)
  assert.doesNotMatch(outlineOptionsSource, /\bEventSource\s*\(/)
})

test('draft generation and confirmation stay behind the Java service boundary', () => {
  assert.match(apiSource, /\/api\/stories\/\$\{req\.story_id\}\/chapters\/\$\{req\.chapter_id\}\/generations/)
  assert.match(apiSource, /\/api\/stories\/\$\{req\.story_id\}\/chapters\/\$\{req\.chapter_id\}\/generations\/\$\{generation\.id\}\/events/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/generations\/\$\{generationId\}\/confirm/)

  assert.doesNotMatch(generationSources, /\/internal\/ai/)
  assert.doesNotMatch(generationSources, /localhost:8000/)
  assert.doesNotMatch(generationSources, /PYTHON_AI_BASE_URL/)
  assert.doesNotMatch(generationSources, /python-ai/i)
})

test('draft UI components use the frontend API client for generation records', () => {
  assert.match(generationHistorySource, /listChapterGenerations/)
  assert.match(generationHistorySource, /getChapterGeneration/)
  assert.match(generationHistorySource, /confirmChapterGeneration/)
  assert.match(sseHookSource, /generateChapterStream/)
  assert.doesNotMatch(generationHistorySource, /\bfetch\s*\(/)
  assert.doesNotMatch(generationHistorySource, /\bEventSource\s*\(/)
  assert.doesNotMatch(sseHookSource, /\bEventSource\s*\(/)
})

test('memory change set API calls stay behind the Java service boundary', () => {
  assert.match(apiSource, /export async function extractMemoryChangeSet/)
  assert.match(apiSource, /export async function listMemoryChangeSets/)
  assert.match(apiSource, /export async function getMemoryChangeSet/)
  assert.match(apiSource, /export async function updateMemoryChangeSet/)
  assert.match(apiSource, /export async function confirmMemoryChangeSet/)
  assert.match(apiSource, /export async function freezeMemoryChangeSet/)

  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/memory-change-sets\/extract/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/memory-change-sets/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/memory-change-sets\/\$\{changeSetId\}/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/memory-change-sets\/\$\{changeSetId\}\/confirm/)
  assert.match(apiSource, /\/api\/stories\/\$\{storyId\}\/chapters\/\$\{chapterId\}\/memory-change-sets\/\$\{changeSetId\}\/freeze/)

  assert.doesNotMatch(memorySources, /\/internal\/ai/)
  assert.doesNotMatch(memorySources, /localhost:8000/)
  assert.doesNotMatch(memorySources, /PYTHON_AI_BASE_URL/)
  assert.doesNotMatch(memorySources, /python-ai/i)
})

test('memory change set panel uses the frontend API client', () => {
  assert.match(memoryChangeSetPanelSource, /extractMemoryChangeSet/)
  assert.match(memoryChangeSetPanelSource, /listMemoryChangeSets/)
  assert.match(memoryChangeSetPanelSource, /updateMemoryChangeSet/)
  assert.match(memoryChangeSetPanelSource, /confirmMemoryChangeSet/)
  assert.match(memoryChangeSetPanelSource, /freezeMemoryChangeSet/)
  assert.doesNotMatch(memoryChangeSetPanelSource, /\bfetch\s*\(/)
  assert.doesNotMatch(memoryChangeSetPanelSource, /\bEventSource\s*\(/)
})

test('memory change set panel advances chapter stage when Java returns only a change set', () => {
  assert.match(memoryChangeSetPanelSource, /onChapterUpdated\?\.\(\{\s*\.\.\.chapter,\s*workflowStage:\s*'memory_pending_confirmation'\s*\}\)/s)
  assert.match(memoryChangeSetPanelSource, /onChapterUpdated\?\.\(\{\s*\.\.\.chapter,\s*workflowStage:\s*'memory_confirmed'\s*\}\)/s)
  assert.match(memoryChangeSetPanelSource, /MEMORY_READY_STAGES\s*=\s*\['memory_confirmed'\]/)
  assert.match(memoryChangeSetPanelSource, /'chapter_confirmed'/)
})
