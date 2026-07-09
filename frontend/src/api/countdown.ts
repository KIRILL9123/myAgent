export interface Countdown {
  id: number;
  title: string;
  target_date: string;
  category: string;
  days_remaining: number;
  created_at: string;
}

export interface CountdownCreateInput {
  title: string;
  target_date: string;
  category?: string;
}

const API_BASE = '/api/countdown';

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

export async function fetchCountdowns(): Promise<Countdown[]> {
  const resp = await fetch(`${API_BASE}/`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to fetch countdowns: ${resp.statusText}`);
  }
  const result = await resp.json();
  if (result.status === 'error') {
    throw new Error(result.message);
  }
  return result.countdowns;
}

export async function createCountdown(input: CountdownCreateInput): Promise<{ id: number; message: string }> {
  const resp = await fetch(`${API_BASE}/`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(input),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to create countdown: ${resp.statusText}`);
  }
  const result = await resp.json();
  if (result.status === 'error') {
    throw new Error(result.message);
  }
  return result;
}

export async function deleteCountdown(id: number): Promise<{ message: string }> {
  const resp = await fetch(`${API_BASE}/${id}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to delete countdown: ${resp.statusText}`);
  }
  const result = await resp.json();
  if (result.status === 'error') {
    throw new Error(result.message);
  }
  return result;
}
