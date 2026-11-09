import { LexiMark } from './LexiMark'

interface LexiLogoProps {
  variant?: 'header' | 'footer'
}

export function LexiLogo({ variant = 'header' }: LexiLogoProps) {
  const compact = variant === 'footer'

  return (
    <span className={`lexi-logo lexi-logo--${variant}`}>
      <LexiMark size={compact ? 26 : 44} />
      <span className="lexi-logo__text">
        <span className="lexi-logo__name">LEXI</span>
        {!compact && (
          <span className="lexi-logo__tagline">Droit &amp; clarté</span>
        )}
      </span>
    </span>
  )
}
