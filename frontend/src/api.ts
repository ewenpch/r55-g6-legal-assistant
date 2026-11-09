export async function errorMessage(response: Response): Promise<string> {
  const data = await response.json().catch(() => ({}))
  const detail = Array.isArray(data.detail)
    ? data.detail[0]?.msg?.replace(/^Value error, /, '')
    : data.detail
  return detail || `Erreur du serveur (${response.status}).`
}
