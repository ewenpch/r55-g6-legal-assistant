import { describe, expect, it } from 'vitest'
import { splitIntoBlocks, tokenize } from './text'

describe('tokenize', () => {
  it('détecte les montants, les dates et les durées', () => {
    const segments = tokenize(
      'Loyer de 750 € payable le 1/10/2026 après 3 mois.',
    )

    expect(segments.filter((segment) => segment.type !== 'text')).toEqual([
      { type: 'amount', value: '750 €' },
      { type: 'date', value: '1/10/2026' },
      { type: 'duration', value: '3 mois' },
    ])
  })
})

describe('splitIntoBlocks', () => {
  it('découpe le texte en phrases', () => {
    expect(splitIntoBlocks('Première phrase. Deuxième phrase.')).toEqual([
      'Première phrase.',
      'Deuxième phrase.',
    ])
  })

  it('privilégie les paragraphes', () => {
    expect(
      splitIntoBlocks('Premier paragraphe.\n\nSecond paragraphe.'),
    ).toEqual(['Premier paragraphe.', 'Second paragraphe.'])
  })
})
