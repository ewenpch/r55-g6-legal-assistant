import { useEffect, useState } from 'react'
import type { User } from './AuthForm'
import DocumentsSection, { type DocumentItem } from './DocumentsSection'
import LogsSection from './LogsSection'
import { errorMessage } from './api'

interface Answer {
  en_clair: string
  a_retenir: string[]
  extrait?: string
}

interface HistoryItem extends Answer {
  id: number
  clause: string
}

function AnswerView({ answer }: { answer: Answer }) {
  return (
    <>
      {answer.extrait && (
        <blockquote className="quote">{answer.extrait}</blockquote>
      )}
      <p>{answer.en_clair}</p>
      {answer.a_retenir.length > 0 && (
        <>
          <h3>À retenir</h3>
          <ul>
            {answer.a_retenir.map((point) => (
              <li key={point}>{point}</li>
            ))}
          </ul>
        </>
      )}
    </>
  )
}

export default function ExplainPage({
  user,
  onLogout,
  onExpired,
}: {
  user: User
  onLogout: () => void
  onExpired: () => void
}) {
  const [text, setText] = useState('')
  const [document, setDocument] = useState<DocumentItem | null>(null)
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [history, setHistory] = useState<HistoryItem[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  const [refresh, setRefresh] = useState(0)

  useEffect(() => {
    fetch('/api/history')
      .then((response) => {
        if (response.status === 401) return onExpired()
        if (response.ok) return response.json().then(setHistory)
      })
      .catch(() => undefined) // l'historique est facultatif
  }, [refresh, onExpired])

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setAnswer(null)
    setError('')
    if (!text.trim()) {
      setError(
        document
          ? 'Écrivez votre demande, par exemple « Explique la clause 3 ».'
          : 'Collez une clause à expliquer.',
      )
      return
    }
    setLoading(true)
    try {
      const response = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text, document_id: document?.id ?? null }),
      })
      if (response.status === 401) return onExpired()
      if (!response.ok) {
        setError(await errorMessage(response))
        return
      }
      setAnswer(await response.json())
    } catch {
      setError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.')
    } finally {
      setLoading(false)
      setRefresh((n) => n + 1) // recharge historique et journal
    }
  }

  return (
    <main className="explain">
      <header className="topbar">
        <span>{user.email}</span>
        <button type="button" onClick={onLogout}>
          Se déconnecter
        </button>
      </header>
      <h1>Expliquer une clause</h1>
      <p className="notice">
        Le texte collé et le document sélectionné sont envoyés à un service d’IA
        externe (Groq) et conservés dans votre compte. N’y mettez pas de données
        personnelles. Ceci n’est pas un conseil juridique.
      </p>
      <DocumentsSection
        selectedId={document?.id ?? null}
        onSelect={setDocument}
      />
      <form onSubmit={handleSubmit}>
        <label htmlFor="clause">
          {document
            ? `Votre demande sur « ${document.filename} »`
            : 'Clause de contrat'}
        </label>
        <textarea
          id="clause"
          rows={document ? 3 : 8}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={
            document
              ? 'Ex. : Explique la clause 3'
              : 'Collez ici une clause de votre contrat…'
          }
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Analyse en cours…' : 'Expliquer'}
        </button>
      </form>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {answer && (
        <section aria-label="Explication" className="answer">
          <h2>Explication</h2>
          <AnswerView answer={answer} />
          <p className="notice">
            Cette explication ne constitue pas un conseil juridique.
          </p>
        </section>
      )}
      {history.length > 0 && (
        <section aria-label="Historique" className="history">
          <h2>Mon historique</h2>
          {history.map((item) => (
            <details key={item.id}>
              <summary>{item.clause.slice(0, 80)}</summary>
              <AnswerView answer={item} />
            </details>
          ))}
        </section>
      )}
      <LogsSection refreshKey={refresh} />
    </main>
  )
}
