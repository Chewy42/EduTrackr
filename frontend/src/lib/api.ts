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

export async function deleteChatSession(jwt: string, sessionId: string): Promise<void> {
	  const res = await fetch(`/api/chat/sessions/${sessionId}`, {
	    method: 'DELETE',
	    headers: {
	      'Authorization': `Bearer ${jwt}`,
	      'Accept': 'application/json',
	    },
	  });
	  if (!res.ok) throw new Error('Failed to delete session');
	}

export async function clearExploreChatSessions(
	  jwt: string,
	  keepSessionId?: string | null,
): Promise<void> {
	  const params = new URLSearchParams({ scope: 'explore' });
	  if (keepSessionId) {
	    params.set('keep_session_id', keepSessionId);
	  }
	  const query = params.toString();
	  const res = await fetch(`/api/chat/sessions?${query}`, {
	    method: 'DELETE',
	    headers: {
	      'Authorization': `Bearer ${jwt}`,
	      'Accept': 'application/json',
	    },
	  });
	  if (!res.ok) throw new Error('Failed to clear sessions');
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

