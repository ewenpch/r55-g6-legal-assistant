export interface Answer {
  en_clair: string
  a_retenir: string[]
  /** Clause citée mot pour mot (question sur un document), vérifiée par le serveur. */
  extrait?: string
}

export interface ErrorBody {
  detail?: string | Array<{ msg?: string }>
}

export interface User {
  id: number
  email: string
}

export interface DocumentItem {
  id: number
  filename: string
  pages: number
  size: number
}

export interface HistoryItem {
  id: number
  clause: string
  en_clair: string
  a_retenir: string[]
}

export interface LogItem {
  id: number
  model: string
  duration_ms: number
  error: string | null
  created_at: string
}

export interface Repere {
  texte: string
  page: number
  contexte: string
}

export interface Terme {
  terme: string
  definition: string
  pages: number[]
}

export interface Reperes {
  montants: Repere[]
  dates: Repere[]
  durees: Repere[]
  termes: Terme[]
}

export interface SearchResult {
  q: string
  total: number
  resultats: { page: number; extrait: string }[]
}
