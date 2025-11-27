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

export type ChatSession = {
  id: string;
  title: string;
  created_at: string;
};

export type ChatMessage = {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: Date;
};

export async function listChatSessions(jwt: string): Promise<ChatSession[]> {
  const res = await fetch('/api/chat/sessions', {
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Accept': 'application/json'
    }
  });
  if (!res.ok) throw new Error('Failed to list sessions');
  return res.json();
}

export async function getChatHistory(jwt: string, sessionId: string): Promise<ChatMessage[]> {
  const res = await fetch(`/api/chat/history/${sessionId}`, {
    headers: {
      'Authorization': `Bearer ${jwt}`,
      'Accept': 'application/json'
    }
  });
  if (!res.ok) throw new Error('Failed to get history');
  const data = await res.json();
  return data.messages || [];
}

