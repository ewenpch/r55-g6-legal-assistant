import type { User } from '../types'
import { LogoutIcon, UserIcon } from './icons'

interface UserBarProps {
  user: User
  onLogout: () => void
}

export function UserBar({ user, onLogout }: UserBarProps) {
  return (
    <div className="userbar">
      <span className="userbar__who">
        <UserIcon size={15} />
        {user.email}
      </span>
      <button className="btn-ghost" type="button" onClick={onLogout}>
        <LogoutIcon size={15} />
        Se déconnecter
      </button>
    </div>
  )
}
