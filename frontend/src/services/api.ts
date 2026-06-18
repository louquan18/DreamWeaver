import type { Chapter, ChapterGeneration, GenerateRequest, GenerateResponse, Story } from '../types'

const API_BASE = ''

export async function healthCheck(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/health`)
  return res.json()
}

export async function generateChapter(req: GenerateRequest): Promise<GenerateResponse> {
  const generation = await createChapterGeneration(req)
  return {
    story_id: req.story_id,
    chapter_id: req.chapter_id,
    draft: generation.draft || '',
    word_count: generation.wordCount || 0,
    execution_history: [],
  }
}

export async function listStories(): Promise<Story[]> {
  const res = await fetch(`${API_BASE}/api/stories`)
  if (!res.ok) {
    throw new Error('Failed to load stories')
  }
  return res.json()
}

export async function createStory(input: {
  title: string
  genre?: string
  description?: string
}): Promise<Story> {
  const res = await fetch(`${API_BASE}/api/stories`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(input),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Failed to create story' }))
    throw new Error(error.message || 'Failed to create story')
  }

  return res.json()
}

export async function listChapters(storyId: string): Promise<Chapter[]> {
  const res = await fetch(`${API_BASE}/api/stories/${storyId}/chapters`)
  if (!res.ok) {
    throw new Error('Failed to load chapters')
  }
  return res.json()
}

export async function createChapter(
  storyId: string,
  input: {
    chapterNumber: number
    title?: string
  },
): Promise<Chapter> {
  const res = await fetch(`${API_BASE}/api/stories/${storyId}/chapters`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      chapterNumber: input.chapterNumber,
      chapter_number: input.chapterNumber,
      title: input.title,
    }),
  })

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Failed to create chapter' }))
    throw new Error(error.message || 'Failed to create chapter')
  }

  return res.json()
}

export async function createChapterGeneration(req: GenerateRequest): Promise<ChapterGeneration> {
  const res = await fetch(
    `${API_BASE}/api/stories/${req.story_id}/chapters/${req.chapter_id}/generations`,
    {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        userId: req.user_id,
        user_id: req.user_id,
        targetWords: req.target_words,
        target_words: req.target_words,
        extraPrompt: req.extra_prompt,
        extra_prompt: req.extra_prompt,
        modelProfile: req.model_profile,
        model_profile: req.model_profile,
        autoAdopt: req.auto_adopt ?? true,
        auto_adopt: req.auto_adopt ?? true,
      }),
    },
  )

  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Failed to create generation' }))
    throw new Error(error.message || 'Failed to create generation')
  }

  return res.json()
}

export async function listChapterGenerations(
  storyId: string,
  chapterId: string,
): Promise<ChapterGeneration[]> {
  const res = await fetch(`${API_BASE}/api/stories/${storyId}/chapters/${chapterId}/generations`)
  if (!res.ok) {
    throw new Error('Failed to load generation history')
  }
  return res.json()
}

export async function getChapterGeneration(
  storyId: string,
  chapterId: string,
  generationId: string,
): Promise<ChapterGeneration> {
  const res = await fetch(
    `${API_BASE}/api/stories/${storyId}/chapters/${chapterId}/generations/${generationId}`,
  )
  if (!res.ok) {
    throw new Error('Failed to load generation detail')
  }
  return res.json()
}

export async function adoptChapterGeneration(
  storyId: string,
  chapterId: string,
  generationId: string,
): Promise<Chapter> {
  const res = await fetch(
    `${API_BASE}/api/stories/${storyId}/chapters/${chapterId}/generations/${generationId}/adopt`,
    {
      method: 'POST',
    },
  )
  if (!res.ok) {
    const error = await res.json().catch(() => ({ message: 'Failed to adopt generation' }))
    throw new Error(error.message || 'Failed to adopt generation')
  }
  return res.json()
}

export function generateChapterStream(
  req: GenerateRequest,
  callbacks: {
    onToken?: (content: string) => void
    onNodeStart?: (node: string, progress: number) => void
    onNodeEnd?: (node: string, progress: number) => void
    onDone?: (data: { story_id: string; chapter_id: string; draft?: string }) => void
    onError?: (message: string) => void
    onCreated?: (generation: ChapterGeneration) => void
  },
): { close: () => void } {
  let eventSource: EventSource | null = null
  let closed = false

  createChapterGeneration(req)
    .then((generation) => {
      if (closed) return
      callbacks.onCreated?.(generation)

      eventSource = new EventSource(
        `${API_BASE}/api/stories/${req.story_id}/chapters/${req.chapter_id}/generations/${generation.id}/events`,
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
        eventSource?.close()
      })

      eventSource.addEventListener('error', (e) => {
        if (eventSource?.readyState === EventSource.CLOSED) return
        const data = (e as MessageEvent).data
        callbacks.onError?.(data ? JSON.parse(data).message : 'Connection error')
        eventSource?.close()
      })
    })
    .catch((error: Error) => {
      callbacks.onError?.(error.message)
    })

  return {
    close: () => {
      closed = true
      eventSource?.close()
    },
  }
}
