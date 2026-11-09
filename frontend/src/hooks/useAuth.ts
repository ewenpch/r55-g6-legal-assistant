import { useCallback, useEffect, useState } from 'react'
import { errorMessage } from '../api'
import type { User } from '../types'

export type AuthMode = 'login' | 'register'

/** undefined = vérification en cours, null = non connecté. */
export function useAuth() {
  const [user, setUser] = useState<User | null | undefined>(undefined)

  useEffect(() => {
    fetch('/api/auth/me')
      .then((response) => (response.ok ? response.json() : null))
      .then(setUser)
      .catch(() => setUser(null))
  }, [])

  /** Renvoie un message d'erreur, ou null si la connexion a réussi. */
  const authenticate = useCallback(
    async (mode: AuthMode, email: string, password: string) => {
      try {
        const response = await fetch(`/api/auth/${mode}`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ email, password }),
        })
        if (!response.ok) return await errorMessage(response)
        setUser(await response.json())
        return null
      } catch {
        return 'Impossible de joindre le serveur. Vérifiez qu’il est démarré.'
      }
    },
    [],
  )

  const logout = useCallback(async () => {
    await fetch('/api/auth/logout', { method: 'POST' }).catch(() => undefined)
    setUser(null)
  }, [])

  const expire = useCallback(() => setUser(null), [])

  return { user, authenticate, logout, expire }
}
