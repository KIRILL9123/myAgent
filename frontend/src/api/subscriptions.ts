import { apiRequest } from './client';

export type SubscriptionStatus = 'PROPOSED' | 'ACTIVE' | 'CANCELLED' | 'EXPIRED';
export type SubscriptionType = 'TRIAL' | 'PAID' | 'UNKNOWN';

export interface SubscriptionFinanceLink {
  status: 'pending_approval' | 'linked' | 'not_eligible';
  approval_id?: string;
  reason?: string;
}

export interface Subscription {
  id: string;
  name: string;
  provider: string | null;
  description: string | null;
  status: SubscriptionStatus;
  subscription_type: SubscriptionType;
  amount: number | null;
  currency: string | null;
  billing_cycle: string | null;
  trial_ends_at: string | null;
  next_charge_at: string | null;
  reminder_at: string | null;
  reminder_sent_at: string | null;
  cancellation_url: string | null;
  cancellation_instructions: string | null;
  confidence: number;
  provenance: Record<string, unknown>;
  source_type: string;
  source_ref: string | null;
  created_at: string;
  updated_at: string;
  finance_link?: SubscriptionFinanceLink;
}

export interface SubscriptionCreateInput {
  name: string;
  subscription_type?: SubscriptionType;
  amount?: number;
  currency?: string;
  trial_ends_at?: string;
  next_charge_at?: string;
  reminder_at?: string;
  cancellation_url?: string;
  cancellation_instructions?: string;
}

const API_BASE = '/api/subscriptions';

const request = <T>(path: string, init: RequestInit = {}) =>
  apiRequest<T>(`${API_BASE}${path}`, {
    ...init,
    headers: init.body ? { 'Content-Type': 'application/json', ...init.headers } : init.headers,
  });

export async function fetchSubscriptions(status?: SubscriptionStatus): Promise<Subscription[]> {
  const query = status ? `?status=${encodeURIComponent(status)}` : '';
  const result = await request<{ subscriptions: Subscription[] }>(`/${query}`);
  return result.subscriptions;
}

export async function createSubscription(input: SubscriptionCreateInput): Promise<Subscription> {
  return request<Subscription>('/', { method: 'POST', body: JSON.stringify(input) });
}

export async function approveSubscription(id: string): Promise<Subscription> {
  return request<Subscription>(`/${id}/approve`, {
    method: 'POST',
    body: JSON.stringify({ provenance: { channel: 'web' } }),
  });
}

export async function cancelSubscription(id: string): Promise<Subscription> {
  return request<Subscription>(`/${id}/cancel`, { method: 'POST' });
}

export async function scanEmailForSubscriptions(
  account: string,
  limit = 20,
): Promise<{
  account: string;
  scanned: number;
  proposals: Subscription[];
  errors: { subject: string; error: string }[];
}> {
  return request('/scan-email', { method: 'POST', body: JSON.stringify({ account, limit }) });
}
