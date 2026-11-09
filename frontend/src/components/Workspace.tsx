import { useCallback, useState } from 'react'
import { useDocuments } from '../hooks/useDocuments'
import { useExplainClause } from '../hooks/useExplainClause'
import { AnswerCard } from './AnswerCard'
import { ClauseForm } from './ClauseForm'
import { DocumentsPanel } from './DocumentsPanel'
import { DocumentTools } from './DocumentTools'
import { EmptyState } from './EmptyState'
import { HistoryPanel } from './HistoryPanel'
import { JusticeGavel } from './JusticeGavel'
import { Loader } from './Loader'
import { LogsPanel } from './LogsPanel'

interface WorkspaceProps {
  onExpired: () => void
}

/** Espace de travail d'un utilisateur connecté : documents, question, résultat, suivi. */
export function Workspace({ onExpired }: WorkspaceProps) {
  const docs = useDocuments()
  const [refresh, setRefresh] = useState(0)
  const onDone = useCallback(() => setRefresh((n) => n + 1), [])
  const { answer, error, loading, explain } = useExplainClause({
    documentId: docs.selected?.id,
    onExpired,
    onDone,
  })

  return (
    <>
      <main className="app__main">
        <div className="app__side">
          <section className="panel" aria-label="Saisie de la clause">
            <ClauseForm
              loading={loading}
              error={error}
              document={docs.selected}
              onSubmit={explain}
            />
          </section>
          <DocumentsPanel
            documents={docs.documents}
            selectedId={docs.selected?.id ?? null}
            error={docs.error}
            uploading={docs.uploading}
            onUpload={docs.upload}
            onSelect={docs.setSelected}
            onRemove={docs.remove}
          />
        </div>
        <div className="app__result" aria-live="polite">
          <JusticeGavel active={answer !== null} />
          {loading ? (
            <Loader />
          ) : answer ? (
            <AnswerCard answer={answer} />
          ) : (
            <EmptyState documentName={docs.selected?.filename} />
          )}
        </div>
      </main>
      <div className="app__extra">
        {docs.selected && (
          <DocumentTools key={docs.selected.id} document={docs.selected} />
        )}
        <HistoryPanel refreshKey={refresh} onExpired={onExpired} />
        <LogsPanel refreshKey={refresh} />
      </div>
    </>
  )
}
