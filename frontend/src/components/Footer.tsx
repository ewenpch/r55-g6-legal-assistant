import { useEffect, useState } from 'react'
import { LexiLogo } from './LexiLogo'
import { ShieldIcon } from './icons'

export function Footer() {
  const [model, setModel] = useState('')

  // Le modèle réellement configuré côté serveur (jamais la clé).
  useEffect(() => {
    fetch('/api/health')
      .then((response) => (response.ok ? response.json() : null))
      .then((data) => setModel(data?.llm?.model ?? ''))
      .catch(() => undefined)
  }, [])

  return (
    <footer className="app__footer">
      <div className="app__footer-brand">
        <LexiLogo variant="footer" />
        <span className="app__footer-tagline">
          La clarté juridique, sans jargon.
        </span>
      </div>
      <div className="app__footer-meta">
        <p>Propulsé par Groq{model ? ` · ${model}` : ''}</p>
        <p>
          <ShieldIcon size={14} />
          Ceci n’est pas un conseil juridique.
        </p>
      </div>
    </footer>
  )
}
