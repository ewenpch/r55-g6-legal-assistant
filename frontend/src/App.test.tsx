import { fireEvent, render, screen } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

type Route = { status: number; body: unknown }

function mockApi(routes: Record<string, Route>) {
  const fn = vi.fn((url: string) => {
    const route = routes[url] ?? { status: 404, body: {} }
    return Promise.resolve({
      ok: route.status < 400,
      status: route.status,
      json: () => Promise.resolve(route.body),
    })
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

const USER = { id: 1, email: 'a@b.fr' }
const ANSWER = {
  en_clair: 'En clair : vous payez le 5.',
  a_retenir: ['Date : le 5'],
}
const SIGNED_IN = {
  '/api/auth/me': { status: 200, body: USER },
  '/api/history': { status: 200, body: [] },
}

describe('App', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the login form when not signed in', async () => {
    mockApi({ '/api/auth/me': { status: 401, body: {} } })
    render(<App />)

    expect(
      await screen.findByRole('heading', { name: 'Connexion' }),
    ).toBeInTheDocument()
    expect(screen.queryByLabelText('Clause de contrat')).not.toBeInTheDocument()
  })

  it('shows the server error when login fails', async () => {
    mockApi({
      '/api/auth/me': { status: 401, body: {} },
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

  it('goes back to the login form after logout', async () => {
    mockApi({ ...SIGNED_IN, '/api/auth/logout': { status: 204, body: {} } })
    render(<App />)

    fireEvent.click(
      await screen.findByRole('button', { name: 'Se déconnecter' }),
    )

    expect(
      await screen.findByRole('heading', { name: 'Connexion' }),
    ).toBeInTheDocument()
  })

  it('shows the explanation when signed in', async () => {
    const fetchMock = mockApi({
      ...SIGNED_IN,
      '/api/explain': { status: 200, body: ANSWER },
    })
    render(<App />)

    fireEvent.change(await screen.findByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Expliquer' }))

    expect(await screen.findByText(/vous payez le 5/)).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/explain',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('shows a clear message when the AI call fails', async () => {
    mockApi({
      ...SIGNED_IN,
      '/api/explain': {
        status: 504,
        body: { detail: 'Le service d’IA a mis trop de temps.' },
      },
    })
    render(<App />)

    fireEvent.change(await screen.findByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Expliquer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('trop de temps')
  })

  it('does not call the server when the field is empty', async () => {
    const fetchMock = mockApi(SIGNED_IN)
    render(<App />)

    fireEvent.click(await screen.findByRole('button', { name: 'Expliquer' }))

    expect(await screen.findByRole('alert')).toBeInTheDocument()
    expect(fetchMock).not.toHaveBeenCalledWith(
      '/api/explain',
      expect.anything(),
    )
  })

  it('uploads a PDF and shows the server error when it is rejected', async () => {
    const fetchMock = mockApi({
      ...SIGNED_IN,
      '/api/documents': {
        status: 422,
        body: {
          detail: 'Aucun texte extractible : ce PDF est peut-être un scan.',
        },
      },
    })
    render(<App />)

    const input = await screen.findByLabelText(/Déposer un PDF/)
    const file = new File(['%PDF-1.4'], 'scan.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })

    expect(await screen.findByRole('alert')).toHaveTextContent('Aucun texte')
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/documents',
      expect.objectContaining({ method: 'POST', body: expect.any(FormData) }),
    )
  })

  it('asks a question about the uploaded document and shows the quote', async () => {
    const doc = { id: 7, filename: 'bail.pdf', pages: 2, size: 2048 }
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      const json = (status: number, body: unknown) =>
        Promise.resolve({
          ok: status < 400,
          status,
          json: () => Promise.resolve(body),
        })
      if (url === '/api/auth/me') return json(200, USER)
      if (url === '/api/history') return json(200, [])
      if (url === '/api/documents' && init?.method === 'POST')
        return json(201, doc)
      if (url === '/api/documents') return json(200, [doc])
      if (url === '/api/explain')
        return json(200, {
          ...ANSWER,
          extrait: 'Article 3 - Le loyer est dû le 5.',
        })
      return json(404, {})
    })
    vi.stubGlobal('fetch', fetchMock)
    render(<App />)

    const file = new File(['%PDF-1.4'], 'bail.pdf', { type: 'application/pdf' })
    fireEvent.change(await screen.findByLabelText(/Déposer un PDF/), {
      target: { files: [file] },
    })
    fireEvent.change(
      await screen.findByLabelText(/Votre demande sur « bail.pdf »/),
      {
        target: { value: 'Explique la clause 3' },
      },
    )
    fireEvent.click(screen.getByRole('button', { name: 'Expliquer' }))

    expect(
      await screen.findByText('Article 3 - Le loyer est dû le 5.'),
    ).toBeInTheDocument()
    const call = fetchMock.mock.calls.find(([url]) => url === '/api/explain')
    expect(JSON.parse(String(call?.[1]?.body))).toEqual({
      text: 'Explique la clause 3',
      document_id: 7,
    })
  })
})
