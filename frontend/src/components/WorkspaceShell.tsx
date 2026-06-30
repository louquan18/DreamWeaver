import type { ReactNode } from 'react'
import './WorkspaceShell.css'

interface WorkspaceShellProps {
  sidebar: ReactNode
  main: ReactNode
  actionRail: ReactNode
}

export function WorkspaceShell({ sidebar, main, actionRail }: WorkspaceShellProps) {
  return (
    <main className="workspace-shell">
      <aside className="story-workspace-slot" aria-label="Novel workspace navigation">
        {sidebar}
      </aside>
      <section className="workspace-main-slot" aria-label="Main workspace">
        {main}
      </section>
      <aside className="workspace-action-slot" aria-label="Context actions">
        {actionRail}
      </aside>
    </main>
  )
}
