import { useEffect, useState } from 'react'
import type { HistoryItem } from '../types'
import { Highlighted } from './Highlighted'
import { ClockIcon } from './icons'

interface HistoryPanelProps {
  refreshKey: number
  onExpired: () => void
}

export function HistoryPanel({ refreshKey, onExpired }: HistoryPanelProps) {
  const [items, setItems] = useState<HistoryItem[]>([])

  useEffect(() => {
    fetch('/api/history')
      .then((response) => {
        if (response.status === 401) return onExpired()
        if (response.ok) return response.json().then(setItems)
      })
      .catch(() => undefined) // l'historique est facultatif
  }, [refreshKey, onExpired])

  if (items.length === 0) return null
  return (
    <section className="panel" aria-label="Historique">
      <h2 className="panel__title">
        <ClockIcon size={16} />
        Mon historique
      </h2>
      <div className="folds">
        {items.map((item) => (
          <details className="fold" key={item.id}>
            <summary>{item.clause.slice(0, 90)}</summary>
            <div className="fold__body">
              <p>
                <Highlighted text={item.en_clair} />
              </p>
              {item.a_retenir.length > 0 && (
                <ul>
                  {item.a_retenir.map((point) => (
                    <li key={point}>{point}</li>
                  ))}
                </ul>
              )}
            </div>
          </details>
        ))}
      </div>
    </section>
  )
}
