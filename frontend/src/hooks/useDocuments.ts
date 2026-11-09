import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '../api'
import type { DocumentItem } from '../types'

/** Documents PDF de l'utilisateur et document sélectionné pour les questions. */
export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [selected, setSelected] = useState<DocumentItem | null>(null)
  const [error, setError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    fetch('/api/documents')
      .then((response) => (response.ok ? response.json() : []))
      .then(setDocuments)
      .catch(() => undefined)
  }, [refresh])

  const upload = useCallback(async (file: File) => {
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
      setSelected(await response.json()) // le document déposé est sélectionné
      setRefresh((n) => n + 1)
    } catch {
      setError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.')
    } finally {
      setUploading(false)
    }
  }, [])

  const remove = useCallback(
    async (id: number) => {
      await fetch(`/api/documents/${id}`, { method: 'DELETE' }).catch(
        () => undefined,
      )
      if (selected?.id === id) setSelected(null)
      setRefresh((n) => n + 1)
    },
    [selected],
  )

  return { documents, selected, setSelected, error, uploading, upload, remove }
}
