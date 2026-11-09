export interface Answer {
  en_clair: string
  a_retenir: string[]
}

export interface ErrorBody {
  detail?: string | Array<{ msg?: string }>
}
