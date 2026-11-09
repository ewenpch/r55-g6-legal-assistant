import { useState } from 'react'
import './App.css'

interface Answer {
  en_clair: string
  a_retenir: string[]
}

function App() {
  const [text, setText] = useState('')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setAnswer(null)
    setError('')
    if (!text.trim()) {
      setError('Collez une clause à expliquer.')
      return
    }
    setLoading(true)
    try {
      const response = await fetch('/api/explain', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        const detail = Array.isArray(data.detail)
          ? data.detail[0]?.msg?.replace(/^Value error, /, '')
          : data.detail
        setError(detail || `Erreur du serveur (${response.status}).`)
        return
      }
      setAnswer(data)
    } catch {
      setError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="explain">
      <h1>Expliquer une clause</h1>
      <p className="notice">
        Le texte collé est envoyé à un service d’IA externe (Groq). N’y mettez
        pas de données personnelles. Ceci n’est pas un conseil juridique.
      </p>
      <form onSubmit={handleSubmit}>
        <label htmlFor="clause">Clause de contrat</label>
        <textarea
          id="clause"
          rows={8}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder="Collez ici une clause de votre contrat…"
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
          <p className="notice">
            Cette explication ne constitue pas un conseil juridique.
          </p>
        </section>
      )}
    </main>
  )
}

export default App
