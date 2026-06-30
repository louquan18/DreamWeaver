import type { ReactNode } from 'react'
import type { Chapter, Story } from '../types'
import type { WorkspaceView } from './workspaceTypes'
import { getWorkspaceNavItem } from './workspaceTypes'

interface WorkspaceMainProps {
  activeView: WorkspaceView
  story: Story | null
  chapter: Chapter | null
  children: ReactNode
}

export function WorkspaceMain({ activeView, story, chapter, children }: WorkspaceMainProps) {
  const view = getWorkspaceNavItem(activeView)

  return (
    <div className="workspace-main-panel">
      <div className="workspace-panel-heading">
        <div>
          <span>{view.label}</span>
          <h2>{story ? story.title : 'No novel selected'}</h2>
          <p>{chapter ? chapterLabel(chapter) : view.detail}</p>
        </div>
        <strong>{view.marker}</strong>
      </div>
      <div className="workspace-panel-body">
        {children}
      </div>
    </div>
  )
}

function chapterLabel(chapter: Chapter) {
  const number = chapter.chapterNumber ?? chapter.chapter_number ?? 0
  const stage = chapter.workflowStage ?? chapter.workflow_stage ?? chapter.status
  return `#${number} ${chapter.title || 'Untitled'} / ${stage?.replaceAll('_', ' ') || 'chapter created'}`
}
