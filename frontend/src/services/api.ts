// API 服务层

import type { GenerateRequest, GenerateResponse } from '../types'

const API_BASE = ''  // Vite proxy handles /api → localhost:8000

// ========== REST API ==========

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`)
  return res.json()
}

export async function generateChapter(req: GenerateRequest): Promise<GenerateResponse> {
  const params = new URLSearchParams({
    story_id: req.story_id,
    chapter_id: req.chapter_id,
    ...(req.user_id ? { user_id: req.user_id } : {}),
  })
  const res = await fetch(`${API_BASE}/api/ai/chapters/generate?${params}`, {
    method: 'POST',
  })
  return res.json()
}

// ========== SSE 流式 ==========

export function generateChapterStream(
  req: GenerateRequest,
  callbacks: {
    onToken?: (content: string) => void
    onNodeStart?: (node: string, progress: number) => void
    onNodeEnd?: (node: string, progress: number) => void
    onDone?: (data: { story_id: string; chapter_id: string }) => void
    onError?: (message: string) => void
  },
): EventSource {
  const params = new URLSearchParams({
    story_id: req.story_id,
    chapter_id: req.chapter_id,
    ...(req.user_id ? { user_id: req.user_id } : {}),
  })

  const eventSource = new EventSource(
    `${API_BASE}/api/ai/chapters/generate-stream?${params}`,
  )

  eventSource.addEventListener('token', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onToken?.(data.content)
  })

  eventSource.addEventListener('node_start', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onNodeStart?.(data.node, data.progress)
  })

  eventSource.addEventListener('node_end', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onNodeEnd?.(data.node, data.progress)
  })

  eventSource.addEventListener('done', (e) => {
    const data = JSON.parse(e.data)
    callbacks.onDone?.(data)
    eventSource.close()
  })

  eventSource.addEventListener('error', (e) => {
    if (eventSource.readyState === EventSource.CLOSED) return
    const data = (e as MessageEvent).data
    callbacks.onError?.(data ? JSON.parse(data).message : 'Connection error')
    eventSource.close()
  })

  return eventSource
}
