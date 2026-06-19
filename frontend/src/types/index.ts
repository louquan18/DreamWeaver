// 前端类型定义

export interface Story {
  id: string
  userId?: string
  user_id?: string
  title: string
  description?: string
  genre?: string
  targetWords?: number
  target_words?: number
  status: string
  createdAt?: string
  updatedAt?: string
  created_at?: string
  updated_at?: string
}

export interface Chapter {
  id: string
  storyId?: string
  story_id?: string
  chapterNumber?: number
  chapter_number?: number
  title?: string
  content?: string
  contentUrl?: string
  content_url?: string
  wordCount?: number
  word_count?: number
  lastGenerationId?: string
  status: string
  workflowStage?: string
  workflow_stage?: string
  createdAt?: string
  updatedAt?: string
  created_at?: string
  updated_at?: string
}

export interface WorkflowStatus {
  current_node: string
  execution_history: string[]
  progress: number
}

// SSE 事件类型
export interface SSEEvent {
  type: 'node_start' | 'node_end' | 'token' | 'progress' | 'done' | 'error'
  data: Record<string, unknown>
}

export interface GenerateRequest {
  story_id: string
  chapter_id: string
  user_id?: string
  target_words?: number
  extra_prompt?: string
  model_profile?: string
  auto_adopt?: boolean
}

export interface GenerateResponse {
  story_id: string
  chapter_id: string
  draft: string
  word_count: number
  execution_history: string[]
}

export interface ChapterGeneration {
  id: string
  storyId: string
  chapterId: string
  userId: string
  status: string
  request?: Record<string, unknown>
  draft?: string
  draftUrl?: string
  wordCount?: number
  modelProfile?: string
  modelName?: string
  executionHistory?: Array<Record<string, unknown>>
  consistencyReport?: Record<string, unknown>
  reviewReport?: Record<string, unknown>
  repairReport?: Record<string, unknown>
  repairResult?: Record<string, unknown>
  autoRepairResult?: Record<string, unknown>
  checkpointId?: string
  errorMessage?: string
  adopted: boolean
  startedAt?: string
  completedAt?: string
  createdAt?: string
  updatedAt?: string
}

export interface BlueprintValidationIssue {
  code: string
  path: string
  message: string
  severity: 'error' | 'warning'
  blocking: boolean
}

export interface NovelBlueprint {
  id?: string
  storyId?: string
  story_id?: string
  sourcePrompt?: string
  source_prompt?: string
  premise: string
  genre?: string | null
  tone?: string | null
  protagonist?: Record<string, unknown>
  mainThread?: Record<string, unknown>
  main_thread?: Record<string, unknown>
  coreConflict?: Record<string, unknown>
  core_conflict?: Record<string, unknown>
  worldSeed?: Record<string, unknown>
  world_seed?: Record<string, unknown>
  writingPreferences?: Record<string, unknown>
  writing_preferences?: Record<string, unknown>
  lockedFacts?: Array<Record<string, unknown>>
  locked_facts?: Array<Record<string, unknown>>
  validationIssues?: BlueprintValidationIssue[]
  validation_issues?: BlueprintValidationIssue[]
  status?: string
  confirmedAt?: string
  supersededAt?: string
  createdAt?: string
  updatedAt?: string
}

export interface BlueprintGenerateRequest {
  sourcePrompt: string
  genre?: string
  tone?: string
  targetWords?: number
  preferences?: Record<string, unknown>
}

export interface BlueprintUpdateRequest {
  sourcePrompt?: string
  premise?: string
  genre?: string
  tone?: string
  protagonist?: Record<string, unknown>
  mainThread?: Record<string, unknown>
  coreConflict?: Record<string, unknown>
  worldSeed?: Record<string, unknown>
  writingPreferences?: Record<string, unknown>
  lockedFacts?: Array<Record<string, unknown>>
}

export interface BlueprintGenerateResult {
  story?: Story
  blueprint: NovelBlueprint
}

export interface BlueprintConfirmRequest {
  editedBlueprint?: BlueprintUpdateRequest
}

export interface BlueprintConfirmResult {
  story?: Story
  blueprint: NovelBlueprint
}

export type OutlineOptionCode = 'A' | 'B' | 'C'
export type OutlineOptionType = 'steady' | 'conflict' | 'foreshadow'

export interface OutlineScene {
  order?: number
  summary?: string
  purpose?: string
  characters?: string[]
  location?: string
  povCharacter?: string
  tension?: string
  outcome?: string
  [key: string]: unknown
}

export interface OutlineCharacter {
  name?: string
  role?: string
  motivation?: string
  stateChange?: string
  state_change?: string
  [key: string]: unknown
}

export interface ForeshadowAction {
  action?: 'plant' | 'strengthen' | 'trigger' | 'resolve' | string
  description?: string
  foreshadowId?: string
  foreshadow_id?: string
  evidence?: string
  payoffHint?: string
  payoff_hint?: string
  [key: string]: unknown
}

export interface MemoryReference {
  memoryType?: string
  memory_type?: string
  memoryId?: string
  memory_id?: string
  referenceId?: string
  summary?: string
  relevance?: string
  [key: string]: unknown
}

export interface ChapterOutlineOption {
  id?: string
  storyId?: string
  chapterId?: string
  optionGroupId?: string
  option_group_id?: string
  optionCode?: OutlineOptionCode
  option_code?: OutlineOptionCode
  optionType?: OutlineOptionType
  option_type?: OutlineOptionType
  titleCandidates?: string[]
  title_candidates?: string[]
  chapterGoal?: string
  chapter_goal?: string
  storySummary?: string
  story_summary?: string
  sceneOutline?: OutlineScene[]
  scene_outline?: OutlineScene[]
  charactersInvolved?: OutlineCharacter[]
  characters_involved?: OutlineCharacter[]
  conflict?: Record<string, unknown>
  highlightMoment?: string
  highlight_moment?: string
  foreshadowActions?: ForeshadowAction[]
  foreshadow_actions?: ForeshadowAction[]
  memoryReferences?: MemoryReference[]
  memory_references?: MemoryReference[]
  whyThisPlan?: string
  why_this_plan?: string
  endingHook?: string
  ending_hook?: string
  riskNotes?: string[]
  risk_notes?: string[]
  status?: string
  createdAt?: string
  updatedAt?: string
}

export interface ChapterOutline {
  id: string
  storyId?: string
  chapterId?: string
  sourceOptionIds?: string[]
  userFeedback?: string
  finalOutline: Record<string, unknown>
  status: string
  confirmedAt?: string
  createdAt?: string
  updatedAt?: string
}

export interface ChapterOutlineConfirmRequest {
  sourceOptionIds?: string[]
  userFeedback?: string
  finalOutline?: Record<string, unknown>
}

export interface ChapterOutlineConfirmResult {
  chapter: Chapter
  outline: ChapterOutline
}

export interface ChapterOutlineOptionsGenerateRequest {
  authorIntent?: Record<string, unknown>
}

export interface ChapterOutlineOptionsGenerateResult {
  chapter: Chapter
  options: ChapterOutlineOption[]
}
