import { LexiMark } from './LexiMark'

export function Loader() {
  return (
    <section
      className="loader"
      aria-live="polite"
      aria-busy="true"
      aria-label="Analyse en cours"
    >
      <div className="loader__emblem" aria-hidden="true">
        <LexiMark size={40} animated />
      </div>
      <div className="loader__text">
        <p className="loader__title">Analyse en cours…</p>
        <p className="loader__hint">
          Lexi lit la clause et la reformule en langage clair.
        </p>
      </div>
      <div className="loader__lines" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
    </section>
  )
}
