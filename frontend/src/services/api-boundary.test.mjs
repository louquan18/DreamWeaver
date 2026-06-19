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
const blueprintSources = `${apiSource}\n${ideaChatSource}`
const outlineSources = `${apiSource}\n${outlineOptionsSource}`

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
