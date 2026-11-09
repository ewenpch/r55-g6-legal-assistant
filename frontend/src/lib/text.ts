export type SegmentType = 'text' | 'amount' | 'date' | 'duration'

export interface Segment {
  type: SegmentType
  value: string
}

const MONTHS =
  'janvier|février|fevrier|mars|avril|mai|juin|juillet|août|aout|septembre|octobre|novembre|décembre|decembre'

const TOKEN_SOURCE = [
  '\\d{1,2}[/.-]\\d{1,2}[/.-]\\d{2,4}',
  `(?:${MONTHS})\\b`,
  '\\b\\d[\\d\\s.,]*\\s?(?:€|euros?|%|\\$)',
  '\\b\\d+\\s?(?:jours?|semaines?|mois|ans?|années?|annees?|heures?)',
].join('|')

function typeOf(value: string): SegmentType {
  if (/(?:€|euros?|%|\$)/i.test(value)) return 'amount'
  if (/\d{1,2}[/.-]\d{1,2}[/.-]\d{2,4}/.test(value)) return 'date'
  if (new RegExp(MONTHS, 'i').test(value)) return 'date'
  return 'duration'
}

export function tokenize(text: string): Segment[] {
  const re = new RegExp(TOKEN_SOURCE, 'gi')
  const segments: Segment[] = []
  let lastIndex = 0
  let match: RegExpExecArray | null

  while ((match = re.exec(text)) !== null) {
    if (match.index > lastIndex) {
      segments.push({ type: 'text', value: text.slice(lastIndex, match.index) })
    }
    segments.push({ type: typeOf(match[0]), value: match[0] })
    lastIndex = match.index + match[0].length
  }

  if (lastIndex < text.length) {
    segments.push({ type: 'text', value: text.slice(lastIndex) })
  }

  return segments
}

export function splitIntoBlocks(text: string): string[] {
  const trimmed = text.trim()
  if (!trimmed) return []

  const paragraphs = trimmed
    .split(/\n{2,}/)
    .map((paragraph) => paragraph.trim())
    .filter(Boolean)

  if (paragraphs.length > 1) return paragraphs

  const sentences = trimmed
    .split(/(?<=[.!?])\s+/)
    .map((sentence) => sentence.trim())
    .filter(Boolean)

  return sentences.length > 1 ? sentences : [trimmed]
}
