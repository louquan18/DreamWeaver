// 前端类型定义

export interface Story {
  id: string
  user_id: string
  title: string
  description?: string
  genre?: string
  target_words?: number
  status: string
  created_at: string
  updated_at: string
}

export interface Chapter {
  id: string
  story_id: string
  chapter_number: number
  title?: string
  content_url?: string
  word_count?: number
  status: string
  created_at: string
  updated_at: string
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
}

export interface GenerateResponse {
  story_id: string
  chapter_id: string
  draft: string
  word_count: number
  execution_history: string[]
}
