import { useCallback, useState } from 'react'
import { errorMessage } from '../api'
import type { Answer } from '../types'

interface ExplainState {
  answer: Answer | null
  error: string
  loading: boolean
}

const EMPTY_STATE: ExplainState = { answer: null, error: '', loading: false }

interface Options {
  /** Document sur lequel porte la demande (« Explique la clause 3 »). */
  documentId?: number | null
  /** Appelé quand la session a expiré (401). */
  onExpired: () => void
  /** Appelé après chaque appel (succès ou échec) pour recharger historique et journal. */
  onDone: () => void
}

export function useExplainClause({ documentId, onExpired, onDone }: Options) {
  const [state, setState] = useState<ExplainState>(EMPTY_STATE)

  const explain = useCallback(
    async (rawText: string) => {
      const text = rawText.trim()
      if (!text) {
        setState({
          answer: null,
          error: documentId
            ? 'Écrivez votre demande, par exemple « Explique la clause 3 ».'
            : 'Collez une clause à expliquer.',
          loading: false,
        })
        return
      }

      setState({ answer: null, error: '', loading: true })
      try {
        const response = await fetch('/api/explain', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ text, document_id: documentId ?? null }),
        })
        if (response.status === 401) {
          setState(EMPTY_STATE)
          onExpired()
          return
        }
        if (!response.ok) {
          setState({
            answer: null,
            error: await errorMessage(response),
            loading: false,
          })
          return
        }
        setState({
          answer: (await response.json()) as Answer,
          error: '',
          loading: false,
        })
      } catch {
        setState({
          answer: null,
          error:
            'Impossible de joindre le serveur. Vérifiez qu’il est démarré.',
          loading: false,
        })
      } finally {
        onDone()
      }
    },
    [documentId, onExpired, onDone],
  )

  return { ...state, explain }
}
