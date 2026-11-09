import { useEffect, useState } from 'react'
import { errorMessage } from './api'

export interface DocumentItem {
  id: number
  filename: string
  pages: number
  size: number
}

export default function DocumentsSection({
  selectedId,
  onSelect,
}: {
  selectedId: number | null
  onSelect: (doc: DocumentItem | null) => void
}) {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [refresh, setRefresh] = useState(0)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)

  useEffect(() => {
    fetch('/api/documents')
      .then((response) => (response.ok ? response.json() : []))
      .then(setDocuments)
      .catch(() => undefined)
  }, [refresh])

  async function handleFile(event: React.ChangeEvent<HTMLInputElement>) {
    const input = event.target
    const file = input.files?.[0]
    if (!file) return
    setError('')
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const response = await fetch('/api/documents', {
        method: 'POST',
        body: form,
      })
      if (!response.ok) {
        setError(await errorMessage(response))
        return
      }
      onSelect(await response.json()) // le document déposé est sélectionné
      setRefresh((n) => n + 1)
    } catch {
      setError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.')
    } finally {
      setUploading(false)
      input.value = ''
    }
  }

  async function remove(id: number) {
    await fetch(`/api/documents/${id}`, { method: 'DELETE' }).catch(
      () => undefined,
    )
    if (id === selectedId) onSelect(null)
    setRefresh((n) => n + 1)
  }

  return (
    <section aria-label="Mes documents" className="documents">
      <h2>Mes documents</h2>
      <label htmlFor="pdf">Déposer un PDF (5 Mo et 10 pages maximum)</label>
      <input
        id="pdf"
        type="file"
        accept="application/pdf,.pdf"
        onChange={handleFile}
        disabled={uploading}
      />
      {uploading && <p className="notice">Envoi en cours…</p>}
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <ul>
        {documents.map((doc) => (
          <li key={doc.id}>
            <label>
              <input
                type="radio"
                name="document"
                checked={doc.id === selectedId}
                onChange={() => onSelect(doc)}
              />{' '}
              {doc.filename} ({doc.pages} p., {Math.ceil(doc.size / 1024)} Ko)
            </label>{' '}
            <button type="button" onClick={() => remove(doc.id)}>
              Supprimer
            </button>
          </li>
        ))}
      </ul>
      {selectedId !== null && (
        <button type="button" className="link" onClick={() => onSelect(null)}>
          Ne plus utiliser de document (coller une clause)
        </button>
      )}
    </section>
  )
}
