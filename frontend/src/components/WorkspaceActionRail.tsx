import type { ReactNode } from 'react'
import type { WorkspaceView } from './workspaceTypes'
import { getWorkspaceNavItem } from './workspaceTypes'

interface WorkspaceActionRailProps {
  activeView: WorkspaceView
  children: ReactNode
}

export function WorkspaceActionRail({ activeView, children }: WorkspaceActionRailProps) {
  const view = getWorkspaceNavItem(activeView)

  return (
    <div className="workspace-action-panel">
      <div className="workspace-action-heading">
        <span>{view.marker}</span>
        <div>
          <h2>{view.label} Actions</h2>
          <p>{view.detail}</p>
        </div>
      </div>
      <div className="workspace-action-body">
        {children}
      </div>
    </div>
  )
}
