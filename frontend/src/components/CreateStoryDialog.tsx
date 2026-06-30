import { useState, type FormEvent } from 'react'
import './CreateStoryDialog.css'

export type CreateStoryIntent = 'create' | 'blueprint'

interface CreateStoryDialogProps {
  open: boolean
  creating?: boolean
  error?: string
  onClose: () => void
  onCreate: (
    input: { title: string; genre?: string; description?: string },
    intent: CreateStoryIntent,
  ) => Promise<void>
}

export function CreateStoryDialog({
  open,
  creating = false,
  error = '',
  onClose,
  onCreate,
}: CreateStoryDialogProps) {
  const [title, setTitle] = useState('')
  const [genre, setGenre] = useState('')
  const [description, setDescription] = useState('')
  const canSubmit = Boolean(title.trim()) && !creating

  if (!open) return null

  async function submit(intent: CreateStoryIntent) {
    if (!canSubmit) return
    try {
      await onCreate({
        title: title.trim(),
        genre: genre.trim() || undefined,
        description: description.trim() || undefined,
      }, intent)
      setTitle('')
      setGenre('')
      setDescription('')
    } catch {
      // The parent renders the error in the dialog.
    }
  }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    void submit('create')
  }

  return (
    <div className="story-dialog-backdrop" role="presentation" onMouseDown={onClose}>
      <section
        className="story-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="story-dialog-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <div className="story-dialog-header">
          <div>
            <span>New novel</span>
            <h2 id="story-dialog-title">Create a workspace</h2>
          </div>
          <button type="button" className="story-dialog-close" onClick={onClose} disabled={creating}>
            X
          </button>
        </div>

        <form className="story-dialog-form" onSubmit={handleSubmit}>
          <label>
            <span>Title</span>
            <input
              type="text"
              value={title}
              onChange={(event) => setTitle(event.target.value)}
              placeholder="Novel title"
              disabled={creating}
              autoFocus
            />
          </label>

          <label>
            <span>Genre</span>
            <input
              type="text"
              value={genre}
              onChange={(event) => setGenre(event.target.value)}
              placeholder="Fantasy, mystery, xianxia..."
              disabled={creating}
            />
          </label>

          <label className="field-wide">
            <span>Seed idea</span>
            <textarea
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              placeholder="A short premise, protagonist, conflict, or mood. This can be used to generate the first blueprint."
              rows={5}
              disabled={creating}
            />
          </label>

          {error && <div className="story-dialog-error">{error}</div>}

          <div className="story-dialog-actions">
            <button type="button" onClick={onClose} disabled={creating}>
              Cancel
            </button>
            <button type="submit" disabled={!canSubmit}>
              {creating ? 'Creating' : 'Create only'}
            </button>
            <button
              type="button"
              className="primary"
              onClick={() => void submit('blueprint')}
              disabled={!canSubmit}
            >
              {creating ? 'Creating' : 'Create and build blueprint'}
            </button>
          </div>
        </form>
      </section>
    </div>
  )
}
