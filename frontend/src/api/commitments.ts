export type CommitmentStatus = 'PROPOSED' | 'ACTIVE' | 'COMPLETED' | 'CANCELLED' | 'EXPIRED';

export interface Commitment {
  id: string;
  title: string;
  description: string | null;
  status: CommitmentStatus;
  confidence: number;
  source_type: string;
  source_ref: string | null;
  owner: string;
  deadline_at: string | null;
  reminder_at: string | null;
  created_at: string;
  updated_at: string;
  related_calendar_event_ids: string[];
}

export interface EmailCommitmentInput {
  account: string;
  sender: string;
  recipient?: string;
  subject: string;
  date?: string;
  preview?: string;
}

const API_BASE = '/api/commitments';

const headers = (json = false): Record<string, string> => ({
  'X-API-Key': (import.meta.env.VITE_API_KEY as string) || '',
  ...(json ? { 'Content-Type': 'application/json' } : {}),
});

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers(Boolean(init.body)), ...(init.headers || {}) },
  });
  if (!response.ok) throw new Error((await response.text()) || `Commitment request failed: ${response.status}`);
  return response.json();
}

export async function fetchCommitments(includeCompleted = true): Promise<Commitment[]> {
  const params = new URLSearchParams({ include_completed: String(includeCompleted) });
  const result = await request<{ commitments: Commitment[] }>(`/?${params}`);
  return result.commitments;
}

export async function approveCommitment(id: string): Promise<Commitment> {
  return request<Commitment>(`/${id}/approve`, { method: 'POST', body: JSON.stringify({ provenance: { channel: 'web' } }) });
}

export async function completeCommitment(id: string): Promise<Commitment> {
  return request<Commitment>(`/${id}/complete`, { method: 'POST' });
}

export async function cancelCommitment(id: string): Promise<Commitment> {
  return request<Commitment>(`/${id}/cancel`, { method: 'POST' });
}

export async function extractEmailCommitments(input: EmailCommitmentInput): Promise<{ proposals: Commitment[] }> {
  return request<{ proposals: Commitment[] }>('/from-email', { method: 'POST', body: JSON.stringify(input) });
}
