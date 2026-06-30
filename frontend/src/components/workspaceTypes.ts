import type { MemoryLibraryType } from '../types'

export type WorkspaceView =
  | 'chapters'
  | 'blueprint'
  | 'characters'
  | 'foreshadows'
  | 'world'
  | 'timeline'
  | 'history'
  | 'agents'

export interface WorkspaceNavItem {
  id: WorkspaceView
  label: string
  detail: string
  marker: string
  memoryType?: MemoryLibraryType
}

export const WORKSPACE_NAV_ITEMS: WorkspaceNavItem[] = [
  {
    id: 'chapters',
    label: 'Chapters',
    detail: 'Draft, outline, memory flow',
    marker: 'CH',
  },
  {
    id: 'blueprint',
    label: 'Blueprint',
    detail: 'Premise and story engine',
    marker: 'BP',
  },
  {
    id: 'characters',
    label: 'Characters',
    detail: 'Cast state and arcs',
    marker: 'CA',
    memoryType: 'characters',
  },
  {
    id: 'foreshadows',
    label: 'Foreshadow',
    detail: 'Clues, triggers, payoffs',
    marker: 'FO',
    memoryType: 'foreshadows',
  },
  {
    id: 'world',
    label: 'World',
    detail: 'Rules, places, factions',
    marker: 'WO',
    memoryType: 'world',
  },
  {
    id: 'timeline',
    label: 'Timeline',
    detail: 'Events and causal order',
    marker: 'TL',
    memoryType: 'timeline',
  },
  {
    id: 'history',
    label: 'Generation History',
    detail: 'Draft records by chapter',
    marker: 'HI',
  },
  {
    id: 'agents',
    label: 'Agent Records',
    detail: 'Live workflow trace',
    marker: 'AG',
  },
]

export function getWorkspaceNavItem(view: WorkspaceView) {
  return WORKSPACE_NAV_ITEMS.find((item) => item.id === view) || WORKSPACE_NAV_ITEMS[0]
}
