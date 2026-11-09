import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

type Reply = { status: number; body?: unknown }
type Routes = Record<string, Reply>

/** Simule l'API : clé « URL » ou « MÉTHODE URL » (la plus spécifique l'emporte). */
function mockApi(routes: Routes) {
  const fn = vi.fn((url: string, init?: RequestInit) => {
    const method = init?.method ?? 'GET'
    const exact = routes[`${method} ${url}`] ?? routes[url]
    const reply = exact ?? { status: 404, body: {} }
    return Promise.resolve({
      ok: reply.status < 400,
      status: reply.status,
      json: () => Promise.resolve(reply.body ?? {}),
    })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

const USER = { id: 1, email: 'a@b.fr' }
const DOC = { id: 7, filename: 'bail.pdf', pages: 2, size: 2048 }
const ANSWER = {
  en_clair: 'Vous payez le loyer avant le 5 de chaque mois.',
  a_retenir: ['Date limite : le 5'],
}
const SIGNED_IN: Routes = {
  '/api/auth/me': { status: 200, body: USER },
  '/api/history': { status: 200, body: [] },
  '/api/llm-logs': { status: 200, body: [] },
  '/api/documents': { status: 200, body: [] },
  '/api/health': { status: 200, body: { llm: { model: 'test-model' } } },
}

async function ask(text: string, label: string | RegExp = 'Clause de contrat') {
  fireEvent.change(await screen.findByLabelText(label), {
    target: { value: text },
  })
  fireEvent.click(screen.getByRole('button', { name: /Expliquer|Poser/ }))
}

async function upload() {
  const file = new File(['%PDF-1.4'], 'bail.pdf', { type: 'application/pdf' })
  fireEvent.change(await screen.findByLabelText(/Déposer un PDF/), {
    target: { files: [file] },
  })
}

describe('App', () => {
  afterEach(() => vi.unstubAllGlobals())

  describe('authentification', () => {
    it('affiche la connexion quand on n’est pas connecté', async () => {
      mockApi({ '/api/auth/me': { status: 401 } })
      render(<App />)

      expect(
        await screen.findByRole('heading', { name: 'Connexion' }),
      ).toBeInTheDocument()
      expect(
        screen.queryByLabelText('Clause de contrat'),
      ).not.toBeInTheDocument()
    })

    it('affiche l’erreur du serveur quand la connexion échoue', async () => {
      mockApi({
        '/api/auth/me': { status: 401 },
        '/api/auth/login': {
          status: 401,
          body: { detail: 'E-mail ou mot de passe incorrect.' },
        },
      })
      render(<App />)

      fireEvent.change(await screen.findByLabelText('Adresse e-mail'), {
        target: { value: 'a@b.fr' },
      })
      fireEvent.change(screen.getByLabelText('Mot de passe'), {
        target: { value: 'mauvais' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

      expect(await screen.findByRole('alert')).toHaveTextContent('incorrect')
    })

    it('ouvre l’espace de travail après une connexion réussie', async () => {
      mockApi({
        ...SIGNED_IN,
        '/api/auth/me': { status: 401 },
        '/api/auth/login': { status: 200, body: USER },
      })
      render(<App />)

      fireEvent.change(await screen.findByLabelText('Adresse e-mail'), {
        target: { value: 'a@b.fr' },
      })
      fireEvent.change(screen.getByLabelText('Mot de passe'), {
        target: { value: 'motdepasse1' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Se connecter' }))

      expect(
        await screen.findByLabelText('Clause de contrat'),
      ).toBeInTheDocument()
      expect(screen.getByText('a@b.fr')).toBeInTheDocument()
    })

    it('revient à la connexion après la déconnexion', async () => {
      mockApi({ ...SIGNED_IN, '/api/auth/logout': { status: 204 } })
      render(<App />)

      fireEvent.click(
        await screen.findByRole('button', { name: /Se déconnecter/ }),
      )

      expect(
        await screen.findByRole('heading', { name: 'Connexion' }),
      ).toBeInTheDocument()
    })

    it('revient à la connexion quand la session expire', async () => {
      mockApi({ ...SIGNED_IN, '/api/explain': { status: 401 } })
      render(<App />)

      await ask('Loyer')

      expect(
        await screen.findByRole('heading', { name: 'Connexion' }),
      ).toBeInTheDocument()
    })
  })

  describe('explication d’une clause', () => {
    it('affiche l’explication et déclenche le marteau', async () => {
      const fetchMock = mockApi({
        ...SIGNED_IN,
        '/api/explain': { status: 200, body: ANSWER },
      })
      const { container } = render(<App />)

      await ask('Loyer')

      expect(await screen.findByText(/Vous payez le loyer/)).toBeInTheDocument()
      expect(screen.getByText('Date limite : le 5')).toBeInTheDocument()
      expect(fetchMock).toHaveBeenCalledWith(
        '/api/explain',
        expect.objectContaining({ method: 'POST' }),
      )
      const gavel = container.querySelector<HTMLElement>('.gavel')
      await waitFor(() => expect(gavel).toHaveClass('gavel--striking'))
    })

    it('affiche un message clair quand l’appel à l’IA échoue', async () => {
      mockApi({
        ...SIGNED_IN,
        '/api/explain': {
          status: 504,
          body: { detail: 'Le service d’IA a mis trop de temps.' },
        },
      })
      const { container } = render(<App />)

      await ask('Loyer')

      expect(await screen.findByRole('alert')).toHaveTextContent(
        'trop de temps',
      )
      expect(container.querySelector('.gavel')).not.toHaveClass(
        'gavel--striking',
      )
    })

    it('n’appelle pas le serveur quand le champ est vide', async () => {
      const fetchMock = mockApi(SIGNED_IN)
      render(<App />)

      fireEvent.click(await screen.findByRole('button', { name: /Expliquer/ }))

      expect(await screen.findByRole('alert')).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith(
        '/api/explain',
        expect.anything(),
      )
    })

    it('affiche le modèle réellement configuré dans le pied de page', async () => {
      mockApi(SIGNED_IN)
      render(<App />)

      expect(
        await screen.findByText(/Propulsé par Groq · test-model/),
      ).toBeInTheDocument()
    })
  })

  describe('documents', () => {
    const WITH_DOCUMENT: Routes = {
      ...SIGNED_IN,
      '/api/documents': { status: 200, body: [DOC] },
      'POST /api/documents': { status: 201, body: DOC },
      '/api/documents/7/reperes': {
        status: 200,
        body: {
          montants: [
            { texte: '650 euros', page: 2, contexte: 'dépôt de 650 euros' },
          ],
          dates: [],
          durees: [{ texte: '3 mois', page: 2, contexte: 'préavis de 3 mois' }],
          termes: [
            { terme: 'préavis', definition: 'Délai avant la fin.', pages: [2] },
          ],
        },
      },
      '/api/documents/7/search?q=pr%C3%A9avis': {
        status: 200,
        body: {
          q: 'préavis',
          total: 1,
          resultats: [{ page: 2, extrait: 'Le préavis est de 3 mois' }],
        },
      },
    }

    it('affiche l’erreur du serveur quand le PDF est refusé', async () => {
      mockApi({
        ...SIGNED_IN,
        'POST /api/documents': {
          status: 422,
          body: {
            detail: 'Aucun texte extractible : ce PDF est peut-être un scan.',
          },
        },
      })
      render(<App />)

      await upload()

      expect(await screen.findByRole('alert')).toHaveTextContent('Aucun texte')
    })

    it('pose une question sur le document déposé et cite l’extrait', async () => {
      const fetchMock = mockApi({
        ...WITH_DOCUMENT,
        '/api/explain': {
          status: 200,
          body: { ...ANSWER, extrait: 'Article 3 - Le loyer est dû le 5.' },
        },
      })
      render(<App />)

      await upload()
      await ask('Explique la clause 3', /Votre demande sur « bail.pdf »/)

      expect(await screen.findByText('Extrait du document')).toBeInTheDocument()
      expect(
        await screen.findByText(/Article 3 - Le loyer est dû le 5\./),
      ).toBeInTheDocument()
      const call = fetchMock.mock.calls.find(([url]) => url === '/api/explain')
      expect(JSON.parse(String(call?.[1]?.body))).toEqual({
        text: 'Explique la clause 3',
        document_id: 7,
      })
    })

    it('montre les repères et la recherche sans appeler l’IA', async () => {
      const fetchMock = mockApi(WITH_DOCUMENT)
      render(<App />)

      await upload()

      expect(await screen.findByText('650 euros')).toBeInTheDocument()
      expect(screen.getByText('Délai avant la fin.')).toBeInTheDocument()

      fireEvent.change(screen.getByLabelText('Rechercher dans le document'), {
        target: { value: 'préavis' },
      })
      fireEvent.click(screen.getByRole('button', { name: 'Rechercher' }))

      expect(await screen.findByText(/1 résultat\(s\)/)).toBeInTheDocument()
      expect(screen.getByText(/Le préavis est de 3 mois/)).toBeInTheDocument()
      expect(fetchMock).not.toHaveBeenCalledWith(
        '/api/explain',
        expect.anything(),
      )
    })
  })

  describe('suivi', () => {
    it('affiche l’historique et le journal des appels', async () => {
      mockApi({
        ...SIGNED_IN,
        '/api/history': {
          status: 200,
          body: [
            {
              id: 1,
              clause: 'Le loyer est dû le 5.',
              en_clair: 'Payez le 5.',
              a_retenir: [],
            },
          ],
        },
        '/api/llm-logs': {
          status: 200,
          body: [
            {
              id: 1,
              model: 'm',
              duration_ms: 464,
              error: null,
              created_at: '2026-11-09 14:55:00',
            },
            {
              id: 2,
              model: 'm',
              duration_ms: 12,
              error: 'Trop de requêtes',
              created_at: '2026-11-09 14:56:00',
            },
          ],
        },
      })
      render(<App />)

      expect(
        await screen.findByText('Le loyer est dû le 5.'),
      ).toBeInTheDocument()
      expect(await screen.findByText(/464 ms/)).toBeInTheDocument()
      expect(screen.getByText('Trop de requêtes')).toBeInTheDocument()
    })
  })
})
