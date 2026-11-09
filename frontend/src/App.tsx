import { AuthPanel } from './components/AuthPanel'
import { BackgroundFX } from './components/BackgroundFX'
import { Footer } from './components/Footer'
import { Header } from './components/Header'
import { Loader } from './components/Loader'
import { UserBar } from './components/UserBar'
import { Workspace } from './components/Workspace'
import { useAuth } from './hooks/useAuth'
import './App.css'

function App() {
  const { user, authenticate, logout, expire } = useAuth()

  return (
    <>
      <BackgroundFX />
      <div className="app">
        {user && <UserBar user={user} onLogout={logout} />}
        <Header />
        {user === undefined ? (
          <div className="app__center">
            <Loader />
          </div>
        ) : user === null ? (
          <div className="app__center">
            <AuthPanel onSubmit={authenticate} />
          </div>
        ) : (
          <Workspace onExpired={expire} />
        )}
        <Footer />
      </div>
    </>
  )
}

export default App
