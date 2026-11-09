import { useEffect, useState } from 'react'

interface LogItem {
  id: number
  model: string
  duration_ms: number
  error: string | null
  created_at: string
  request: string
}

// `refreshKey` change après chaque appel à l'IA pour recharger le journal.
export default function LogsSection({ refreshKey }: { refreshKey: number }) {
  const [logs, setLogs] = useState<LogItem[]>([])

  useEffect(() => {
    fetch('/api/llm-logs')
      .then((response) => (response.ok ? response.json() : []))
      .then(setLogs)
      .catch(() => undefined)
  }, [refreshKey])

  if (logs.length === 0) return null
  return (
    <section aria-label="Journal des appels à l'IA" className="logs">
      <h2>Journal des appels à l’IA</h2>
      <ul>
        {logs.map((log) => (
          <li key={log.id}>
            {log.created_at} · {log.model} · {log.duration_ms} ms ·{' '}
            {log.error ? (
              <span className="error">Échec : {log.error}</span>
            ) : (
              'OK'
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
