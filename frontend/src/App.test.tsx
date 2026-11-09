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
    render(<App />)

    fireEvent.change(screen.getByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Expliquer' }))

    expect(await screen.findByText(/vous payez le 5/)).toBeInTheDocument()
    expect(screen.getByText('Date limite : le 5')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/explain',
      expect.objectContaining({ method: 'POST' }),
    )
  })

  it('shows a clear message when the call fails', async () => {
    mockFetch(504, {
      detail: 'Le service d’IA a mis trop de temps à répondre.',
    })
    render(<App />)

    fireEvent.change(screen.getByLabelText('Clause de contrat'), {
      target: { value: 'Loyer' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Expliquer' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('trop de temps')
  })

  it('does not call the server when the field is empty', async () => {
    const fetchMock = mockFetch(200, { en_clair: 'x', a_retenir: [] })
    render(<App />)

    fireEvent.click(screen.getByRole('button', { name: 'Expliquer' }))

    await waitFor(() => expect(screen.getByRole('alert')).toBeInTheDocument())
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
