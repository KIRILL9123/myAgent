import type { EmailMessage, EmailSendInput } from '../types';

export type { EmailMessage, EmailSendInput } from '../types';

const API_BASE = '/api/mail';

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

export async function fetchUnreadEmails(account: string): Promise<EmailMessage[]> {
  const params = new URLSearchParams({ account });
  const resp = await fetch(`${API_BASE}/unread?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to fetch unread emails: ${resp.statusText}`);
  }
  return resp.json();
}

export async function searchEmails(query: string, account: string): Promise<EmailMessage[]> {
  const params = new URLSearchParams({ query, account });
  const resp = await fetch(`${API_BASE}/search?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to search emails: ${resp.statusText}`);
  }
  return resp.json();
}

export async function sendEmail(input: EmailSendInput): Promise<{ status: string; message: string }> {
  const resp = await fetch(`${API_BASE}/send`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(input),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to send email: ${resp.statusText}`);
  }
  return resp.json();
}
