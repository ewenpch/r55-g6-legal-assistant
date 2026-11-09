import { useCallback, useEffect, useState } from 'react'
import './App.css'
import AuthForm, { type User } from './AuthForm'
import ExplainPage from './ExplainPage'

function App() {
  // undefined = vérification en cours, null = non connecté
  const [user, setUser] = useState<User | null | undefined>(undefined)

  useEffect(() => {
    fetch('/api/auth/me')
      .then((response) => (response.ok ? response.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
    setUser(null)
  }, [])
  const expired = useCallback(() => setUser(null), [])

  if (user === undefined) return <p className="notice">Chargement…</p>
  if (user === null) return <AuthForm onLogin={setUser} />
  return <ExplainPage user={user} onLogout={logout} onExpired={expired} />
}

export default App
