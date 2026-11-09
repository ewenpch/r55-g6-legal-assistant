import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { errorMessage } from '../api'
import type { DocumentItem, Repere, Reperes, SearchResult } from '../types'
import { Alert } from './Alert'
import { SearchIcon } from './icons'

const GROUPS: {
  key: 'montants' | 'dates' | 'durees'
  title: string
  token: 'amount' | 'date' | 'duration'
}[] = [
  { key: 'montants', title: 'Montants', token: 'amount' },
  { key: 'dates', title: 'Dates', token: 'date' },
  { key: 'durees', title: 'Durées', token: 'duration' },
]

function Chip({ item, token }: { item: Repere; token: string }) {
  return (
    <li className="chip" title={item.contexte}>
      <mark className={`answer__token answer__token--${token}`}>
        {item.texte}
      </mark>
      <span className="chip__page">p. {item.page}</span>
    </li>
  )
}

interface DocumentToolsProps {
  document: DocumentItem
}

/** Fonctions sans IA : repères détectés par règles et recherche dans le texte. */
export function DocumentTools({ document }: DocumentToolsProps) {
  const [reperes, setReperes] = useState<Reperes | null>(null)
  const [query, setQuery] = useState('')
  const [result, setResult] = useState<SearchResult | null>(null)
  const [error, setError] = useState('')

  useEffect(() => {
    let cancelled = false
    fetch(`/api/documents/${document.id}/reperes`)
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => {
        if (!cancelled) setReperes(data)
      })
      .catch(() => undefined)
    return () => {
      cancelled = true
    }
  }, [document.id])

  async function handleSearch(event: FormEvent) {
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
        `/api/documents/${document.id}/search?q=${encodeURIComponent(q)}`,
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
    <section className="panel tools" aria-label="Repères et recherche">
      <h2 className="panel__title">
        <SearchIcon size={16} />
        Repères de « {document.filename} »
      </h2>
      <p className="panel__sub">Détectés automatiquement, sans IA.</p>

      {GROUPS.map(({ key, title, token }) =>
        reperes && reperes[key].length > 0 ? (
          <div className="tools__group" key={key}>
            <h3>{title}</h3>
            <ul className="chips">
              {reperes[key].map((item) => (
                <Chip
                  item={item}
                  token={token}
                  key={`${item.texte}-${item.page}`}
                />
              ))}
            </ul>
          </div>
        ) : null,
      )}

      {reperes && reperes.termes.length > 0 && (
        <div className="tools__group">
          <h3>Termes à connaître</h3>
          <ul className="terms">
            {reperes.termes.map((t) => (
              <li key={t.terme}>
                <strong>{t.terme}</strong>
                <span className="chip__page">p. {t.pages.join(', ')}</span>
                <p>{t.definition}</p>
              </li>
            ))}
          </ul>
        </div>
      )}

      <form className="searchbar" onSubmit={handleSearch} role="search">
        <label htmlFor="search">Rechercher dans le document</label>
        <div className="searchbar__row">
          <input
            id="search"
            type="search"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Ex. : préavis"
          />
          <button className="btn btn--small" type="submit">
            Rechercher
          </button>
        </div>
      </form>
      {error && <Alert message={error} />}
      {result && (
        <div className="search-results" aria-label="Résultats de recherche">
          <p className="panel__sub">
            {result.total === 0
              ? `Aucun résultat pour « ${result.q} ».`
              : `${result.total} résultat(s) pour « ${result.q} » :`}
          </p>
          <ul>
            {result.resultats.map((hit, index) => (
              <li key={index}>
                <span className="chip__page">p. {hit.page}</span> {hit.extrait}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}
