import { apiRequest } from './client';

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
  project_id: string | null;
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

const request = <T>(path: string, init: RequestInit = {}) =>
  apiRequest<T>(`${API_BASE}${path}`, {
    ...init,
    headers: init.body ? { 'Content-Type': 'application/json', ...init.headers } : init.headers,
  });

export async function fetchCommitments(includeCompleted = true): Promise<Commitment[]> {
  const params = new URLSearchParams({ include_completed: String(includeCompleted) });
  const result = await request<{ commitments: Commitment[] }>(`/?${params}`);
  return result.commitments;
}

export async function approveCommitment(id: string): Promise<Commitment> {
  return request<Commitment>(`/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ provenance: { channel: 'web' } }),
  });
}

export async function completeCommitment(id: string): Promise<Commitment> {
  return request<Commitment>(`/${id}/complete`, { method: 'POST' });
}

export async function updateCommitment(id: string, changes: { deadline_at?: string | null; reminder_at?: string | null }): Promise<Commitment> {
  return request<Commitment>(`/${id}`, { method: 'PATCH', body: JSON.stringify(changes) });
}

export async function cancelCommitment(id: string): Promise<Commitment> {
  return request<Commitment>(`/${id}/cancel`, { method: 'POST' });
}

export async function extractEmailCommitments(input: EmailCommitmentInput): Promise<{ proposals: Commitment[] }> {
  return request<{ proposals: Commitment[] }>('/from-email', { method: 'POST', body: JSON.stringify(input) });
}
