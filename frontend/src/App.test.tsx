import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { afterEach, describe, expect, it, vi } from 'vitest'
import App from './App'

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: status < 400,
    status,
    json: () => Promise.resolve(body),
  })
  vi.stubGlobal('fetch', fn)
  return fn
}

describe('App', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('shows the explanation returned by the server', async () => {
    const fetchMock = mockFetch(200, {
      en_clair: 'En clair : vous payez le 5.',
      a_retenir: ['Date limite : le 5'],
    })
    const { container } = render(<App />)

    fireEvent.change(screen.getByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Expliquer/ }))

    expect(await screen.findByText(/vous payez le 5/)).toBeInTheDocument()
    expect(screen.getByText('Date limite : le 5')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/explain',
      expect.objectContaining({ method: 'POST' }),
    )

    const gavel = container.querySelector<HTMLElement>('.gavel')
    expect(gavel).toHaveAttribute('aria-hidden', 'true')
    await waitFor(() => expect(gavel).toHaveClass('gavel--striking'))
  })

  it('shows a clear message when the call fails', async () => {
    mockFetch(504, {
      detail: 'Le service d’IA a mis trop de temps à répondre.',
    })
    const { container } = render(<App />)
    const gavel = container.querySelector<HTMLElement>('.gavel')

    fireEvent.change(screen.getByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Expliquer/ }))

    expect(await screen.findByRole('alert')).toHaveTextContent('trop de temps')
    expect(gavel).not.toHaveClass('gavel--striking')
  })

  it('does not call the server when the field is empty', async () => {
    const fetchMock = mockFetch(200, { en_clair: 'x', a_retenir: [] })
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: /Expliquer/ }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })

  it('shows a loading state while waiting for the server', async () => {
    let resolveFetch: (value: unknown) => void = () => {}
    const pending = new Promise((resolve) => {
      resolveFetch = resolve
    })
    vi.stubGlobal('fetch', vi.fn().mockReturnValue(pending))
    render(<App />)

    fireEvent.change(screen.getByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: /Expliquer/ }))

    expect(
      await screen.findByRole('region', { name: 'Analyse en cours' }),
    ).toBeInTheDocument()

    resolveFetch({
      ok: true,
      status: 200,
      json: () => Promise.resolve({ en_clair: 'Terminé.', a_retenir: [] }),
    })

    expect(await screen.findByText('Terminé.')).toBeInTheDocument()
  })
})
