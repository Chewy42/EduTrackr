import config from '../../config/app.json'

export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${config.apiBaseUrl}/health`, {
    headers: { 'Accept': 'application/json' },
  })
  if (!res.ok) {
    throw new Error(`Health check failed: ${res.status}`)
  }
  return res.json()
}

