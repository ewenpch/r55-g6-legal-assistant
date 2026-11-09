import { ShieldIcon } from './icons'

interface LegalNoticeProps {
  variant?: 'inline' | 'footer'
}

export function LegalNotice({ variant = 'inline' }: LegalNoticeProps) {
  return (
    <p className={`notice notice--${variant}`} role="note">
      <span className="notice__icon" aria-hidden="true">
        <ShieldIcon size={16} />
      </span>
      <span>
        Le texte saisi et le document sélectionné sont envoyés à un service d’IA
        externe (Groq) et conservés dans votre compte. N’y mettez pas de données
        personnelles. Cette application ne fournit pas de conseil juridique.
      </span>
    </p>
  )
}
