const API_BASE = '/api';

export interface ChatResponse {
  response: string;
  tool_calls: string[];
  requires_confirmation: boolean;
}

const getHeaders = (withJson = false) => {
  const apiKey = (import.meta.env.VITE_API_KEY as string) || '';
  const headers: Record<string, string> = {
    'X-API-Key': apiKey,
  };
  if (withJson) {
    headers['Content-Type'] = 'application/json';
  }
  return headers;
};

export function generateSessionId(): string {
  if (typeof self !== 'undefined' && self.crypto && self.crypto.randomUUID) {
    return self.crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function sendChatMessage(
  message: string,
  sessionId: string
): Promise<ChatResponse> {
  const resp = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to send chat message: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchChatHistory(sessionId: string): Promise<{ history: any[] }> {
  const resp = await fetch(`${API_BASE}/history/${sessionId}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    throw new Error(`Failed to fetch chat history: ${resp.statusText}`);
  }
  return resp.json();
}
