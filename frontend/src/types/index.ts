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
  checkpointId?: string
  errorMessage?: string
  adopted: boolean
  startedAt?: string
  completedAt?: string
  createdAt?: string
  updatedAt?: string
}
