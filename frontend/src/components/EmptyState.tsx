import { LexiMark } from './LexiMark'
import { LaurelIcon } from './icons'

interface EmptyStateProps {
  documentName?: string
}

export function EmptyState({ documentName }: EmptyStateProps) {
  return (
    <section className="empty" aria-label="Aucune analyse">
      <div className="empty__emblem" aria-hidden="true">
        <LaurelIcon className="empty__laurel empty__laurel--left" size={42} />
        <LexiMark size={38} />
        <LaurelIcon className="empty__laurel empty__laurel--right" size={42} />
      </div>
      <p className="empty__title">Votre explication apparaîtra ici</p>
      <p className="empty__hint">
        {documentName
          ? `Demandez par exemple « Explique la clause 3 » : Lexi la retrouve dans ${documentName}.`
          : 'Collez une clause ou déposez un contrat : Lexi l’explique en langage clair.'}
      </p>
    </section>
  )
}
