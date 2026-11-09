import { useState } from 'react'
import type { FormEvent } from 'react'
import type { AuthMode } from '../hooks/useAuth'
import { Alert } from './Alert'
import { ShieldIcon, UserIcon } from './icons'

interface AuthPanelProps {
  /** Renvoie un message d'erreur, ou null en cas de succès. */
  onSubmit: (
    mode: AuthMode,
    email: string,
    password: string,
  ) => Promise<string | null>
}

export function AuthPanel({ onSubmit }: AuthPanelProps) {
  const [mode, setMode] = useState<AuthMode>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const isLogin = mode === 'login'

  async function handleSubmit(event: FormEvent) {
    event.preventDefault()
    setError('')
    setLoading(true)
    const message = await onSubmit(mode, email, password)
    setLoading(false)
    if (message) setError(message)
  }

  return (
    <section className="panel panel--auth" aria-label="Authentification">
      <form className="auth" onSubmit={handleSubmit}>
        <h2 className="auth__title">
          <UserIcon size={18} />
          {isLogin ? 'Connexion' : 'Créer un compte'}
        </h2>
        <div className="field">
          <label htmlFor="email">Adresse e-mail</label>
          <input
            id="email"
            type="email"
            autoComplete="email"
            required
            value={email}
            onChange={(event) => setEmail(event.target.value)}
          />
        </div>
        <div className="field">
          <label htmlFor="password">Mot de passe</label>
          <input
            id="password"
            type="password"
            autoComplete={isLogin ? 'current-password' : 'new-password'}
            required
            minLength={isLogin ? undefined : 8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
          />
          {!isLogin && <p className="field__hint">8 caractères minimum.</p>}
        </div>
        {error && <Alert message={error} />}
        <button className="btn" type="submit" disabled={loading}>
          {loading && <span className="spinner" aria-hidden="true" />}
          {isLogin ? 'Se connecter' : 'Créer mon compte'}
        </button>
        <button
          className="btn-link"
          type="button"
          onClick={() => {
            setMode(isLogin ? 'register' : 'login')
            setError('')
          }}
        >
          {isLogin
            ? 'Pas de compte ? Inscrivez-vous'
            : 'Déjà un compte ? Connectez-vous'}
        </button>
        <p className="notice">
          <span className="notice__icon" aria-hidden="true">
            <ShieldIcon size={16} />
          </span>
          <span>
            Votre mot de passe est haché (bcrypt) et vos documents ne sont
            visibles que de vous.
          </span>
        </p>
      </form>
    </section>
  )
}
