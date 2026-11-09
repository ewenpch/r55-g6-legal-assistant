import { useEffect, useState } from 'react'
import type { LogItem } from '../types'
import { ScalesIcon } from './icons'

// `refreshKey` change après chaque appel à l'IA pour recharger le journal.
export function LogsPanel({ refreshKey }: { refreshKey: number }) {
  const [logs, setLogs] = useState<LogItem[]>([])

  useEffect(() => {
    fetch('/api/llm-logs')
      .then((response) => (response.ok ? response.json() : []))
      .then(setLogs)
      .catch(() => undefined)
  }, [refreshKey])

  if (logs.length === 0) return null
  return (
    <section className="panel" aria-label="Journal des appels à l'IA">
      <h2 className="panel__title">
        <ScalesIcon size={16} />
        Journal des appels à l’IA
      </h2>
      <ul className="logs">
        {logs.map((log) => (
          <li key={log.id} className={`log${log.error ? ' log--error' : ''}`}>
            <span className="log__status">{log.error ? 'Échec' : 'OK'}</span>
            <span className="log__meta">
              {log.created_at} · {log.model} · {log.duration_ms} ms
            </span>
            {log.error && <span className="log__error">{log.error}</span>}
          </li>
        ))}
      </ul>
    </section>
  )
}
