import { tokenize } from '../lib/text'

/** Texte dont les montants, dates et durées sont mis en valeur (jetons de la DA). */
export function Highlighted({ text }: { text: string }) {
  return (
    <>
      {tokenize(text).map((segment, index) =>
        segment.type === 'text' ? (
          <span key={index}>{segment.value}</span>
        ) : (
          <mark
            className={`answer__token answer__token--${segment.type}`}
            key={index}
          >
            {segment.value}
          </mark>
        ),
      )}
    </>
  )
}
