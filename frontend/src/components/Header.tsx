import { LexiLogo } from './LexiLogo'
import { SealIcon } from './icons'

export function Header() {
  return (
    <header className="hero">
      <div className="hero__brand">
        <LexiLogo />
        <span className="hero__badge">
          <SealIcon size={12} />
          IA · Groq
        </span>
      </div>
      <p className="hero__eyebrow">Assistance juridique augmentée</p>
      <h1 className="hero__title">La clause, en clair.</h1>
      <p className="hero__subtitle">
        Collez une clause de bail, de travail ou d’abonnement, ou déposez votre
        contrat en PDF : Lexi retrouve l’article demandé, l’éclaire en langage
        clair et retient l’essentiel.
      </p>
      <div className="hero__rule" aria-hidden="true">
        <span className="hero__rule-line" />
        <span className="hero__rule-diamond" />
        <span className="hero__rule-line" />
      </div>
    </header>
  )
}
