import type { ChangeEvent } from 'react'
import type { DocumentItem } from '../types'
import { Alert } from './Alert'
import { ScrollIcon, TrashIcon, UploadIcon } from './icons'

interface DocumentsPanelProps {
  documents: DocumentItem[]
  selectedId: number | null
  error: string
  uploading: boolean
  onUpload: (file: File) => void
  onSelect: (doc: DocumentItem | null) => void
  onRemove: (id: number) => void
}

export function DocumentsPanel({
  documents,
  selectedId,
  error,
  uploading,
  onUpload,
  onSelect,
  onRemove,
}: DocumentsPanelProps) {
  function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const input = event.target
    const file = input.files?.[0]
    if (file) onUpload(file)
    input.value = '' // permet de redéposer le même fichier
  }

  return (
    <section className="panel" aria-label="Mes documents">
      <h2 className="panel__title">
        <ScrollIcon size={16} />
        Mes documents
      </h2>
      <label className="dropzone" htmlFor="pdf">
        <UploadIcon size={22} />
        <span className="dropzone__text">
          <strong>Déposer un PDF</strong>
          <small>5 Mo et 10 pages maximum, texte sélectionnable</small>
        </span>
        <input
          id="pdf"
          className="visually-hidden"
          type="file"
          accept="application/pdf,.pdf"
          onChange={handleFile}
          disabled={uploading}
        />
      </label>
      {uploading && (
        <p className="panel__status" role="status">
          <span className="spinner spinner--gold" aria-hidden="true" />
          Envoi en cours…
        </p>
      )}
      {error && <Alert message={error} />}
      {documents.length > 0 && (
        <ul className="doclist">
          {documents.map((doc) => (
            <li
              key={doc.id}
              className={`doc${doc.id === selectedId ? ' doc--active' : ''}`}
            >
              <label className="doc__pick">
                <input
                  className="visually-hidden"
                  type="radio"
                  name="document"
                  checked={doc.id === selectedId}
                  onChange={() => onSelect(doc)}
                />
                <span className="doc__radio" aria-hidden="true" />
                <span className="doc__name">{doc.filename}</span>
                <span className="doc__meta">
                  {doc.pages} p. · {Math.ceil(doc.size / 1024)} Ko
                </span>
              </label>
              <button
                className="icon-btn"
                type="button"
                aria-label={`Supprimer ${doc.filename}`}
                onClick={() => onRemove(doc.id)}
              >
                <TrashIcon size={16} />
              </button>
            </li>
          ))}
        </ul>
      )}
      {selectedId !== null && (
        <button
          className="btn-link"
          type="button"
          onClick={() => onSelect(null)}
        >
          Ne plus utiliser de document (coller une clause)
        </button>
      )}
    </section>
  )
}
