import { useCallback, useRef, useState } from 'react'
import { generateChapterStream } from '../services/api'
import type { GenerateRequest } from '../types'

export interface WorkflowState {
  status: 'idle' | 'connecting' | 'generating' | 'done' | 'error'
  currentNode: string
  progress: number
  draft: string
  executionHistory: string[]
  errorMessage: string
  generationId: string
  completionSeq: number
}

const NODE_PROGRESS: Record<string, number> = {
  load_runtime_context: 5,
  novel_context: 15,
  plan_chapter: 30,
  generate_draft: 50,
  check_consistency: 70,
  review: 80,
  rewrite: 85,
  commit: 100,
}

export function useSSE() {
  const [state, setState] = useState<WorkflowState>({
    status: 'idle',
    currentNode: '',
    progress: 0,
    draft: '',
    executionHistory: [],
    errorMessage: '',
    generationId: '',
    completionSeq: 0,
  })

  const eventSourceRef = useRef<{ close: () => void } | null>(null)

  const startGeneration = useCallback((req: GenerateRequest) => {
    setState((prev) => ({
      ...prev,
      status: 'connecting',
      currentNode: '',
      progress: 0,
      draft: '',
      executionHistory: [],
      errorMessage: '',
      generationId: '',
    }))

    eventSourceRef.current = generateChapterStream(req, {
      onCreated: (generation) => {
        setState((prev) => ({
          ...prev,
          generationId: generation.id,
        }))
      },
      onToken: (content) => {
        setState((prev) => ({
          ...prev,
          status: 'generating',
          draft: prev.draft + content,
        }))
      },
      onNodeStart: (node, progress) => {
        setState((prev) => ({
          ...prev,
          currentNode: node,
          progress: progress || NODE_PROGRESS[node] || prev.progress,
        }))
      },
      onNodeEnd: (node) => {
        setState((prev) => ({
          ...prev,
          executionHistory: [...prev.executionHistory, node],
        }))
      },
      onDone: (data) => {
        setState((prev) => ({
          ...prev,
          status: 'done',
          progress: 100,
          draft: prev.draft || data.draft || '',
          completionSeq: prev.completionSeq + 1,
        }))
      },
      onError: (message) => {
        setState((prev) => ({
          ...prev,
          status: 'error',
          errorMessage: message,
          completionSeq: prev.completionSeq + 1,
        }))
      },
    })
  }, [])

  const cancel = useCallback(() => {
    eventSourceRef.current?.close()
    setState((prev) => ({ ...prev, status: 'idle' }))
  }, [])

  const reset = useCallback(() => {
    eventSourceRef.current?.close()
    setState({
      status: 'idle',
      currentNode: '',
      progress: 0,
      draft: '',
      executionHistory: [],
      errorMessage: '',
      generationId: '',
      completionSeq: 0,
    })
  }, [])

  return { state, startGeneration, cancel, reset }
}
