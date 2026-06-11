// SSE Hook - 管理流式生成状态

import { useState, useCallback, useRef } from 'react'
import { generateChapterStream } from '../services/api'
import type { GenerateRequest } from '../types'

export interface WorkflowState {
  status: 'idle' | 'connecting' | 'generating' | 'done' | 'error'
  currentNode: string
  progress: number
  draft: string
  executionHistory: string[]
  errorMessage: string
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
  })

  const eventSourceRef = useRef<EventSource | null>(null)

  const startGeneration = useCallback((req: GenerateRequest) => {
    // 重置状态
    setState({
      status: 'connecting',
      currentNode: '',
      progress: 0,
      draft: '',
      executionHistory: [],
      errorMessage: '',
    })

    const es = generateChapterStream(req, {
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
      onNodeEnd: (node, _progress) => {
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
          // 兜底：如果 token 流没有内容，用 done 事件里的 draft
          draft: prev.draft || data.draft || '',
        }))
      },
      onError: (message) => {
        setState((prev) => ({
          ...prev,
          status: 'error',
          errorMessage: message,
        }))
      },
    })

    eventSourceRef.current = es
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
    })
  }, [])

  return { state, startGeneration, cancel, reset }
}
