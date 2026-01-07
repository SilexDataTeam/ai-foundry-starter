import { getKeycloak } from '../context/AuthContext'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || ''

async function refreshTokenIfNeeded(): Promise<string | null> {
  const keycloak = getKeycloak()
  if (!keycloak) return null

  try {
    // Refresh if token expires in less than 30 seconds
    await keycloak.updateToken(30)
    return keycloak.token ?? null
  } catch (error) {
    console.error('Token refresh failed:', error)
    keycloak.login()
    return null
  }
}

export async function fetchWithAuth(
  url: string,
  options: RequestInit = {}
): Promise<Response> {
  const token = await refreshTokenIfNeeded()

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }),
    ...options.headers,
  }

  return fetch(`${API_BASE_URL}${url}`, {
    ...options,
    headers,
  })
}

export const api = {
  getChats: () => fetchWithAuth('/chats'),

  saveChats: (chats: Record<string, unknown>) =>
    fetchWithAuth('/chats', {
      method: 'POST',
      body: JSON.stringify({ chats }),
    }),

  deleteChat: (chatId: string) =>
    fetchWithAuth(`/chats/${chatId}`, {
      method: 'DELETE',
    }),

  generateChatTitle: (message: string) =>
    fetchWithAuth('/generate_chat_title', {
      method: 'POST',
      body: JSON.stringify({ initial_message: message }),
    }),

  streamEvents: (inputData: unknown) =>
    fetchWithAuth('/stream_events', {
      method: 'POST',
      body: JSON.stringify({ input_data: inputData }),
      headers: { Accept: 'text/event-stream' },
    }),

  sendFeedback: (data: {
    score: number
    text: string
    run_id: string
    log_type: string
  }) =>
    fetchWithAuth('/feedback', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  getConfig: () => fetchWithAuth('/config'),
}
