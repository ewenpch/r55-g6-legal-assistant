import { useCallback, useState } from 'react'
import type { Answer, ErrorBody } from '../types'

interface ExplainState {
  answer: Answer | null
  error: string
  loading: boolean
}

const EMPTY_STATE: ExplainState = { answer: null, error: '', loading: false }

export function useExplainClause() {
  const [state, setState] = useState<ExplainState>(EMPTY_STATE)

  const explain = useCallback(async (rawText: string) => {
    const text = rawText.trim()
    if (!text) {
      setState({
        answer: null,
        error: 'Collez une clause à expliquer.',
        loading: false,
      })
      return
    }

    setState({ answer: null, error: '', loading: true })
    try {
      const response = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      const data = (await response.json().catch(() => ({}))) as Answer &
        ErrorBody

      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail[0]?.msg?.replace(/^Value error, /, '')
          : data.detail
        setState({
          answer: null,
          error: detail || `Erreur du serveur (${response.status}).`,
          loading: false,
        })
        return
      }

      setState({ answer: data, error: '', loading: false })
    } catch {
      setState({
        answer: null,
        error: 'Impossible de joindre le serveur. Vérifiez qu’il est démarré.',
        loading: false,
      })
    }
  }, [])

  return { ...state, explain }
}
