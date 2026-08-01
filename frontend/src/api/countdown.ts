import { apiRequest } from './client';

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

export async function fetchCountdowns(): Promise<Countdown[]> {
  const result = await apiRequest<{ status?: string; message?: string; countdowns: Countdown[] }>(`${API_BASE}/`);
  if (result.status === 'error') {
    throw new Error(result.message);
  }
  return result.countdowns;
}

export async function createCountdown(input: CountdownCreateInput): Promise<{ id: number; message: string }> {
  const result = await apiRequest<{ status?: string; message: string; id: number }>(`${API_BASE}/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
  if (result.status === 'error') {
    throw new Error(result.message);
  }
  return result;
}

export async function deleteCountdown(id: number): Promise<{ message: string }> {
  const result = await apiRequest<{ status?: string; message: string }>(`${API_BASE}/${id}`, {
    method: 'DELETE',
  });
  if (result.status === 'error') {
    throw new Error(result.message);
  }
  return result;
}
