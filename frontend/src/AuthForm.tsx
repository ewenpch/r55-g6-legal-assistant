import { useState } from 'react'
import { errorMessage } from './api'

export interface User {
  id: number
  email: string
}

export default function AuthForm({
  onLogin,
}: {
  onLogin: (user: User) => void
}) {
  const [mode, setMode] = useState<'login' | 'register'>('login')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault()
    setError('')
    setLoading(true)
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })
      if (!response.ok) {
        setError(await errorMessage(response))
        return
      }
      onLogin(await response.json())
    } catch {
      setError('Impossible de joindre le serveur. Vérifiez qu’il est démarré.')
    } finally {
      setLoading(false)
    }
  }

  const isLogin = mode === 'login'
  return (
    <main className="explain">
      <h1>{isLogin ? 'Connexion' : 'Créer un compte'}</h1>
      <form onSubmit={handleSubmit}>
        <label htmlFor="email">Adresse e-mail</label>
        <input
          id="email"
          type="email"
          autoComplete="email"
          required
          value={email}
          onChange={(event) => setEmail(event.target.value)}
        />
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
        {!isLogin && <p className="notice">8 caractères minimum.</p>}
        <button type="submit" disabled={loading}>
          {isLogin ? 'Se connecter' : 'Créer mon compte'}
        </button>
      </form>
      {error && (
        <p role="alert" className="error">
          {error}
        </p>
      )}
      <button
        type="button"
        className="link"
        onClick={() => {
          setMode(isLogin ? 'register' : 'login')
          setError('')
        }}
      >
        {isLogin
          ? 'Pas de compte ? Inscrivez-vous'
          : 'Déjà un compte ? Connectez-vous'}
      </button>
    </main>
  )
}
