import type {
  FinanceSummary,
  RecurringTemplate,
  Transaction,
  TransactionCreateInput,
} from '../types';

export type {
  FinanceSummary,
  RecurringTemplate,
  Transaction,
  TransactionCreateInput,
} from '../types';

const API_BASE = '/api/finance';

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

export async function fetchTransactions(startDate: string, endDate: string, category?: string): Promise<Transaction[]> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  if (category) params.append('category', category);
  
  const resp = await fetch(`${API_BASE}/transactions?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to fetch transactions: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchSummary(startDate: string, endDate: string): Promise<FinanceSummary> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  const resp = await fetch(`${API_BASE}/summary?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to fetch summary: ${resp.statusText}`);
  }
  return resp.json();
}

export async function createTransaction(input: TransactionCreateInput): Promise<Transaction> {
  const resp = await fetch(`${API_BASE}/transactions`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(input),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to create transaction: ${resp.statusText}`);
  }
  return resp.json();
}

export async function deleteTransaction(id: number): Promise<{ status: string; message: string }> {
  const resp = await fetch(`${API_BASE}/transactions/${id}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to delete transaction: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchRecurringTemplates(): Promise<RecurringTemplate[]> {
  const resp = await fetch(`${API_BASE}/recurring`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to fetch recurring templates: ${resp.statusText}`);
  }
  return resp.json();
}

export async function deleteRecurringTemplate(id: number): Promise<{ status: string; message: string }> {
  const resp = await fetch(`${API_BASE}/recurring/${id}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to delete recurring template: ${resp.statusText}`);
  }
  return resp.json();
}
