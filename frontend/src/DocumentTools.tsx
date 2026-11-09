import { useEffect, useState } from 'react'
import { errorMessage } from './api'

interface Repere {
  texte: string
  page: number
  contexte: string
}

interface Terme {
  terme: string
  definition: string
  pages: number[]
}

interface Reperes {
  montants: Repere[]
  dates: Repere[]
  durees: Repere[]
  termes: Terme[]
}

interface SearchResult {
  q: string
  total: number
  resultats: { page: number; extrait: string }[]
}

const SECTIONS: { key: 'montants' | 'dates' | 'durees'; title: string }[] = [
  { key: 'montants', title: 'Montants' },
  { key: 'dates', title: 'Dates' },
  { key: 'durees', title: 'Durées' },
]

// Fonctions sans IA : repères détectés par règles et recherche dans le texte.
export default function DocumentTools({ documentId }: { documentId: number }) {
  const [reperes, setReperes] = useState<Reperes | null>(null)
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResult | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    fetch(`/api/documents/${documentId}/reperes`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled) setReperes(data)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [documentId])

  async function handleSearch(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setResult(null)
    const q = query.trim()
    if (q.length < 2) {
      setError('Tapez au moins 2 caractères.')
      return
    }
    try {
      const response = await fetch(
        `/api/documents/${documentId}/search?q=${encodeURIComponent(q)}`,
      )
      if (!response.ok) {
        setError(await errorMessage(response))
        return
      }
      setResult(await response.json())
    } catch {
      setError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.')
    }
  }

  return (
    <section aria-label="Repères et recherche" className="tools">
      <h2>Repères du document</h2>
      {reperes && (
        <>
          {SECTIONS.map(({ key, title }) =>
            reperes[key].length > 0 ? (
              <div key={key}>
                <h3>{title}</h3>
                <ul>
                  {reperes[key].map((item) => (
                    <li
                      key={`${item.texte}-${item.page}`}
                      title={item.contexte}
                    >
                      <strong>{item.texte}</strong> (p. {item.page}) :{' '}
                      <span className="context">{item.contexte}</span>
                    </li>
                  ))}
                </ul>
              </div>
            ) : null,
          )}
          {reperes.termes.length > 0 && (
            <div>
              <h3>Termes à connaître</h3>
              <ul>
                {reperes.termes.map((t) => (
                  <li key={t.terme}>
                    <strong>{t.terme}</strong> (p. {t.pages.join(', ')}) :{' '}
                    {t.definition}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </>
      )}
      <form onSubmit={handleSearch}>
        <label htmlFor="search">Rechercher dans le document</label>
        <input
          id="search"
          type="search"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Ex. : préavis"
        />
        <button type="submit">Rechercher</button>
      </form>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      {result && (
        <div aria-label="Résultats de recherche">
          <p>
            {result.total === 0
              ? `Aucun résultat pour « ${result.q} ».`
              : `${result.total} résultat(s) pour « ${result.q} » :`}
          </p>
          <ul>
            {result.resultats.map((hit, index) => (
              <li key={index}>
                p. {hit.page} : {hit.extrait}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
