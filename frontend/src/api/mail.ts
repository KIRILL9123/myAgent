import type { EmailMessage, EmailSendInput } from '../types';
import { apiRequest } from './client';

export type { EmailMessage, EmailSendInput } from '../types';

const API_BASE = '/api/mail';

export async function fetchUnreadEmails(account: string): Promise<EmailMessage[]> {
  const params = new URLSearchParams({ account });
  return apiRequest<EmailMessage[]>(`${API_BASE}/unread?${params}`);
}

export async function searchEmails(query: string, account: string): Promise<EmailMessage[]> {
  const params = new URLSearchParams({ query, account });
  return apiRequest<EmailMessage[]>(`${API_BASE}/search?${params}`);
}

export async function sendEmail(input: EmailSendInput): Promise<{ status: string; message: string }> {
  return apiRequest<{ status: string; message: string }>(`${API_BASE}/send`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}
