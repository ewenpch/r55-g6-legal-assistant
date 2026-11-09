import { AnswerCard } from './components/AnswerCard'
import { BackgroundFX } from './components/BackgroundFX'
import { ClauseForm } from './components/ClauseForm'
import { EmptyState } from './components/EmptyState'
import { Header } from './components/Header'
import { JusticeGavel } from './components/JusticeGavel'
import { LexiLogo } from './components/LexiLogo'
import { Loader } from './components/Loader'
import { ShieldIcon } from './components/icons'
import { useExplainClause } from './hooks/useExplainClause'
import './App.css'

function App() {
  const { answer, error, loading, explain } = useExplainClause()

  return (
    <>
      <BackgroundFX />
      <div className="app">
        <Header />
        <main className="app__main">
          <section className="panel" aria-label="Saisie de la clause">
            <ClauseForm loading={loading} error={error} onSubmit={explain} />
          </section>
          <div className="app__result" aria-live="polite">
            <JusticeGavel active={answer !== null} />
            {loading ? (
              <Loader />
            ) : answer ? (
              <AnswerCard answer={answer} />
            ) : (
              <EmptyState />
            )}
          </div>
        </main>
        <footer className="app__footer">
          <div className="app__footer-brand">
            <LexiLogo variant="footer" />
            <span className="app__footer-tagline">
              La clarté juridique, sans jargon.
            </span>
          </div>
          <div className="app__footer-meta">
            <p>Propulsé par Groq · openai/gpt-oss-20b</p>
            <p>
              <ShieldIcon size={14} />
              Ceci n’est pas un conseil juridique.
            </p>
          </div>
        </footer>
      </div>
    </>
  )
}

export default App
