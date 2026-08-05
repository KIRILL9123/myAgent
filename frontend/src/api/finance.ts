import type {
  FinanceSummary,
  FinanceForecast,
  RecurringTemplate,
  Transaction,
  TransactionCreateInput,
} from '../types';
import { apiRequest } from './client';

export type {
  FinanceSummary,
  FinanceForecast,
  RecurringTemplate,
  Transaction,
  TransactionCreateInput,
} from '../types';

const API_BASE = '/api/finance';

export async function fetchTransactions(startDate: string, endDate: string, category?: string): Promise<Transaction[]> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  if (category) params.append('category', category);
  
  return apiRequest<Transaction[]>(`${API_BASE}/transactions?${params}`);
}

export async function fetchSummary(startDate: string, endDate: string): Promise<FinanceSummary> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiRequest<FinanceSummary>(`${API_BASE}/summary?${params}`);
}

export async function fetchForecast(months = 3): Promise<FinanceForecast> {
  return apiRequest<FinanceForecast>(`${API_BASE}/forecast?months=${months}`);
}

export async function createTransaction(input: TransactionCreateInput): Promise<Transaction> {
  return apiRequest<Transaction>(`${API_BASE}/transactions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function deleteTransaction(id: number): Promise<{ status: string; message: string }> {
  return apiRequest<{ status: string; message: string }>(`${API_BASE}/transactions/${id}`, {
    method: 'DELETE',
  });
}

export async function fetchRecurringTemplates(): Promise<RecurringTemplate[]> {
  return apiRequest<RecurringTemplate[]>(`${API_BASE}/recurring`);
}

export async function deleteRecurringTemplate(id: number): Promise<{ status: string; message: string }> {
  return apiRequest<{ status: string; message: string }>(`${API_BASE}/recurring/${id}`, {
    method: 'DELETE',
  });
}
