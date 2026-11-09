import { LexiMark } from './LexiMark'
import { LaurelIcon } from './icons'

export function EmptyState() {
  return (
    <section className="empty" aria-label="Aucune analyse">
      <div className="empty__emblem" aria-hidden="true">
        <LaurelIcon className="empty__laurel empty__laurel--left" size={42} />
        <LexiMark size={38} />
        <LaurelIcon className="empty__laurel empty__laurel--right" size={42} />
      </div>
      <p className="empty__title">Votre explication apparaîtra ici</p>
      <p className="empty__hint">
        Collez une clause : Lexi l’explique en langage clair.
      </p>
    </section>
  )
}
