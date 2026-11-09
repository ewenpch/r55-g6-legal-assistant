import { useState } from 'react'
import type { FormEvent } from 'react'
import type { DocumentItem } from '../types'
import { Alert } from './Alert'
import { LegalNotice } from './LegalNotice'
import { GavelIcon, QuillIcon, ShieldIcon } from './icons'

const MAX_CHARS = 4000

interface ClauseFormProps {
  loading: boolean
  error: string
  /** Document sélectionné : le champ devient une demande (« Explique la clause 3 »). */
  document: DocumentItem | null
  onSubmit: (text: string) => void
}

export function ClauseForm({
  loading,
  error,
  document,
  onSubmit,
}: ClauseFormProps) {
  const [text, setText] = useState('')
  const nearLimit = MAX_CHARS - text.length <= 200

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    onSubmit(text)
  }

  return (
    <form className="clause-form" onSubmit={handleSubmit} noValidate>
      <div className="clause-form__head">
        <label htmlFor="clause">
          <QuillIcon size={15} />
          {document
            ? `Votre demande sur « ${document.filename} »`
            : 'Clause de contrat'}
        </label>
        <span
          className={`clause-form__count${nearLimit ? ' clause-form__count--warn' : ''}`}
          aria-live="polite"
        >
          {text.length} / {MAX_CHARS}
        </span>
      </div>
      <div className="clause-form__field">
        <textarea
          id="clause"
          rows={document ? 3 : 8}
          maxLength={MAX_CHARS}
          value={text}
          onChange={(event) => setText(event.target.value)}
          placeholder={
            document
              ? 'Ex. : Explique la clause 3'
              : 'Collez ici une clause de votre contrat…'
          }
          disabled={loading}
        />
      </div>
      {error && <Alert message={error} />}
      <div className="clause-form__actions">
        <button type="submit" disabled={loading}>
          {loading ? (
            <>
              <span className="spinner" aria-hidden="true" />
              Analyse en cours…
            </>
          ) : (
            <>
              <GavelIcon className="clause-form__gavel" size={18} />
              {document ? 'Poser la question' : 'Expliquer la clause'}
            </>
          )}
        </button>
        <span className="clause-form__hint">
          <ShieldIcon size={14} />
          Réponse en quelques secondes
        </span>
      </div>
      <LegalNotice />
    </form>
  )
}
