import type { Chapter, Story } from '../types'
import type { WorkspaceView } from './workspaceTypes'
import { WORKSPACE_NAV_ITEMS } from './workspaceTypes'

interface StoryWorkspaceSidebarProps {
  stories: Story[]
  chapters: Chapter[]
  selectedStoryId: string
  selectedChapterId: string
  activeView: WorkspaceView
  loadingStories: boolean
  loadingChapters: boolean
  selectionError: string
  isRunning: boolean
  onOpenCreateStory: () => void
  onRefreshStories: () => void
  onSelectStory: (storyId: string) => void
  onSelectChapter: (chapterId: string) => void
  onSelectView: (view: WorkspaceView) => void
}

export function StoryWorkspaceSidebar({
  stories,
  chapters,
  selectedStoryId,
  selectedChapterId,
  activeView,
  loadingStories,
  loadingChapters,
  selectionError,
  isRunning,
  onOpenCreateStory,
  onRefreshStories,
  onSelectStory,
  onSelectChapter,
  onSelectView,
}: StoryWorkspaceSidebarProps) {
  const selectedStory = stories.find((story) => story.id === selectedStoryId)
  const busy = loadingStories || isRunning

  return (
    <div className="story-sidebar">
      <div className="story-sidebar-head">
        <div>
          <span>Novel workspace</span>
          <h2>{selectedStory?.title || 'Select a novel'}</h2>
        </div>
        <div className="story-sidebar-head-actions">
          <button type="button" onClick={onOpenCreateStory} disabled={isRunning}>
            +
          </button>
          <button type="button" onClick={onRefreshStories} disabled={busy}>
            {loadingStories ? '...' : 'Sync'}
          </button>
        </div>
      </div>

      <label className="story-switcher">
        <span>Active novel</span>
        <select
          value={selectedStoryId}
          onChange={(event) => onSelectStory(event.target.value)}
          disabled={busy || stories.length === 0}
        >
          <option value="">No novel selected</option>
          {stories.map((story) => (
            <option key={story.id} value={story.id}>
              {story.title}
            </option>
          ))}
        </select>
      </label>

      <nav className="workspace-nav" aria-label="Workspace views">
        <div className="story-sidebar-section-title">Library</div>
        {WORKSPACE_NAV_ITEMS.map((item) => (
          <button
            type="button"
            key={item.id}
            className={item.id === activeView ? 'active' : ''}
            onClick={() => onSelectView(item.id)}
            aria-current={item.id === activeView ? 'page' : undefined}
          >
            <span>{item.marker}</span>
            <div>
              <strong>{item.label}</strong>
              <small>{item.detail}</small>
            </div>
          </button>
        ))}
      </nav>

      <div className="sidebar-chapters">
        <div className="story-sidebar-section-title">
          Chapters {loadingChapters ? '/ loading' : `/${chapters.length}`}
        </div>
        {!selectedStoryId ? (
          <div className="sidebar-empty">Select a novel first.</div>
        ) : chapters.length === 0 ? (
          <div className="sidebar-empty">No chapters yet.</div>
        ) : (
          <div className="sidebar-chapter-list">
            {chapters.map((chapter) => (
              <button
                type="button"
                key={chapter.id}
                className={chapter.id === selectedChapterId ? 'active' : ''}
                onClick={() => onSelectChapter(chapter.id)}
                disabled={isRunning}
              >
                <strong>#{chapter.chapterNumber ?? chapter.chapter_number ?? 0}</strong>
                <span>{chapter.title || 'Untitled'}</span>
              </button>
            ))}
          </div>
        )}
      </div>

      {selectionError && <div className="story-sidebar-error">{selectionError}</div>}
    </div>
  )
}
