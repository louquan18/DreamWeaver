import { useCallback, useRef, useState } from 'react'
import { generateChapterStream } from '../services/api'
import type { ChapterGeneration, GenerateRequest } from '../types'

export type WorkflowStatus = 'idle' | 'connecting' | 'generating' | 'done' | 'error'

export type AgentEventType =
  | 'connect'
  | 'generation_created'
  | 'node_start'
  | 'node_end'
  | 'token'
  | 'done'
  | 'error'
  | 'cancel'

export interface AgentEvent {
  id: string
  type: AgentEventType
  label: string
  detail?: string
  node?: string
  timestamp: string
}

export interface WorkflowState {
  status: WorkflowStatus
  currentNode: string
  progress: number
  draft: string
  executionHistory: string[]
  errorMessage: string
  generationId: string
  agentEvents: AgentEvent[]
  tokenEventCount: number
  tokenCharCount: number
  tokenPreview: string
  completionSeq: number
  generation: ChapterGeneration | null
}

const MAX_AGENT_EVENTS = 20

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

const NODE_LABELS: Record<string, string> = {
  load_runtime_context: 'Runtime context',
  novel_context: 'Novel memory',
  plan_chapter: 'Chapter planning',
  generate_draft: 'Draft generation',
  check_consistency: 'Consistency check',
  review: 'Quality review',
  rewrite: 'Rewrite pass',
  commit: 'Commit result',
}

function appendAgentEvent(events: AgentEvent[], event: AgentEvent) {
  return [...events, event].slice(-MAX_AGENT_EVENTS)
}

function upsertTokenEvent(events: AgentEvent[], event: AgentEvent) {
  const lastEvent = events.at(-1)
  if (lastEvent?.type !== 'token') {
    return appendAgentEvent(events, event)
  }

  return [...events.slice(0, -1), { ...lastEvent, ...event }]
}

function resolveProgress(node: string, progress: number | undefined, fallback: number) {
  if (typeof progress === 'number' && Number.isFinite(progress)) return progress
  return NODE_PROGRESS[node] || fallback
}

function getNodeLabel(node: string) {
  return NODE_LABELS[node] || node.replaceAll('_', ' ')
}

function normalizeTokenPreview(content: string) {
  return content.replace(/\s+/g, ' ').trim().slice(0, 80)
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
    agentEvents: [],
    tokenEventCount: 0,
    tokenCharCount: 0,
    tokenPreview: '',
    completionSeq: 0,
    generation: null,
  })

  const eventSourceRef = useRef<{ close: () => void } | null>(null)
  const nextEventIdRef = useRef(0)

  const createAgentEvent = useCallback((
    type: AgentEventType,
    label: string,
    detail?: string,
    node?: string,
  ): AgentEvent => ({
    id: String(++nextEventIdRef.current),
    type,
    label,
    detail,
    node,
    timestamp: new Date().toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
    }),
  }), [])

  const startGeneration = useCallback((req: GenerateRequest) => {
    eventSourceRef.current?.close()
    setState((prev) => ({
      ...prev,
      status: 'connecting',
      currentNode: '',
      progress: 0,
      draft: '',
      executionHistory: [],
      errorMessage: '',
      generationId: '',
      agentEvents: [
        createAgentEvent(
          'connect',
          'Connecting to generation stream',
          `Chapter ${req.chapter_id}`,
        ),
      ],
      tokenEventCount: 0,
      tokenCharCount: 0,
      tokenPreview: '',
      generation: null,
    }))

    eventSourceRef.current = generateChapterStream(req, {
      onCreated: (generation) => {
        setState((prev) => ({
          ...prev,
          generationId: generation.id,
          generation,
          agentEvents: appendAgentEvent(
            prev.agentEvents,
            createAgentEvent(
              'generation_created',
              'Generation created',
              generation.id,
            ),
          ),
        }))
      },
      onToken: (content) => {
        setState((prev) => ({
          ...prev,
          status: 'generating',
          draft: prev.draft + content,
          tokenEventCount: prev.tokenEventCount + 1,
          tokenCharCount: prev.tokenCharCount + content.length,
          tokenPreview: normalizeTokenPreview(content) || prev.tokenPreview,
          agentEvents: upsertTokenEvent(
            prev.agentEvents,
            createAgentEvent(
              'token',
              'Draft tokens streaming',
              `${prev.tokenEventCount + 1} events, ${(
                prev.tokenCharCount + content.length
              ).toLocaleString()} chars`,
            ),
          ),
        }))
      },
      onNodeStart: (node, progress) => {
        setState((prev) => ({
          ...prev,
          status: 'generating',
          currentNode: node,
          progress: resolveProgress(node, progress, prev.progress),
          agentEvents: appendAgentEvent(
            prev.agentEvents,
            createAgentEvent(
              'node_start',
              `Started ${getNodeLabel(node)}`,
              `${resolveProgress(node, progress, prev.progress)}%`,
              node,
            ),
          ),
        }))
      },
      onNodeEnd: (node, progress) => {
        setState((prev) => ({
          ...prev,
          progress: resolveProgress(node, progress, prev.progress),
          executionHistory: [...prev.executionHistory, node],
          agentEvents: appendAgentEvent(
            prev.agentEvents,
            createAgentEvent(
              'node_end',
              `Finished ${getNodeLabel(node)}`,
              `${resolveProgress(node, progress, prev.progress)}%`,
              node,
            ),
          ),
        }))
      },
      onDone: (data) => {
        setState((prev) => ({
          ...prev,
          status: 'done',
          progress: 100,
          draft: prev.draft || data.draft || '',
          errorMessage: '',
          generation: data.generation
            ? {
                ...data.generation,
                executionHistory: data.generation.executionHistory?.length
                  ? data.generation.executionHistory
                  : prev.executionHistory.map((node) => ({ node, status: 'succeeded' })),
              }
            : prev.generation,
          agentEvents: appendAgentEvent(
            prev.agentEvents,
            createAgentEvent(
              'done',
              'Generation complete',
              `${(prev.draft || data.draft || '').length.toLocaleString()} chars ready`,
            ),
          ),
          completionSeq: prev.completionSeq + 1,
        }))
      },
      onError: (message) => {
        setState((prev) => ({
          ...prev,
          status: 'error',
          errorMessage: message,
          agentEvents: appendAgentEvent(
            prev.agentEvents,
            createAgentEvent('error', 'Stream error', message),
          ),
          completionSeq: prev.completionSeq + 1,
        }))
      },
    })
  }, [createAgentEvent])

  const cancel = useCallback(() => {
    eventSourceRef.current?.close()
    setState((prev) => ({
      ...prev,
      status: 'idle',
      agentEvents: appendAgentEvent(
        prev.agentEvents,
        createAgentEvent('cancel', 'Generation stopped by user'),
      ),
    }))
  }, [createAgentEvent])

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
      agentEvents: [],
      tokenEventCount: 0,
      tokenCharCount: 0,
      tokenPreview: '',
      completionSeq: 0,
      generation: null,
    })
  }, [])

  return { state, startGeneration, cancel, reset }
}
