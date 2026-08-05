import type { CalendarEvent } from './calendar';

export type StateHealth = 'clear' | 'watch' | 'attention';

export interface StateAlert {
  severity: 'critical' | 'high' | 'medium' | 'low';
  type: string;
  title: string;
  detail: string;
  due_at: string | null;
  target: string | null;
}

export interface StateTaskSummary {
  id: string;
  title: string;
  status: string;
  deadline_at: string | null;
  owner: string;
}

export interface StateSubscriptionSummary {
  id: string | number;
  name: string;
  status: string;
  trial_ends_at: string | null;
  next_charge_at: string | null;
  amount: number | null;
  currency: string | null;
}

export interface StateDeadlineSummary {
  id: number;
  title: string;
  target_date: string;
  days_remaining: number;
  category?: string | null;
}

export interface StateSnapshot {
  generated_at: string;
  timezone: string;
  health: StateHealth;
  headline: string;
  counts: {
    active_commitments: number;
    proposed_commitments: number;
    active_subscriptions: number;
    proposed_subscriptions: number;
    deadlines_next_30_days: number;
    calendar_events_today: number;
    unread_emails: number;
    alerts_total: number;
    alerts_critical: number;
    conflicts: number;
  };
  alerts: StateAlert[];
  next_actions: StateAlert[];
  domains: {
    commitments: StateTaskSummary[];
    subscriptions: StateSubscriptionSummary[];
    deadlines: StateDeadlineSummary[];
    calendar: { status: string; events: CalendarEvent[]; error: string | null };
    conflicts: { status: string; conflicts: Array<Record<string, unknown>>; error?: string };
    finance: { total_income: number; total_expense: number; net_balance: number };
    mail: { status: string; unread_count: number; accounts: Array<Record<string, unknown>>; error: string | null };
  };
}

export interface StateHistoryItem {
  snapshot_date: string;
  generated_at: string;
  health: StateHealth;
  headline: string;
  counts: StateSnapshot['counts'];
  alerts: StateAlert[];
}

export interface StateReport extends StateSnapshot {
  history: StateHistoryItem[];
  changes: Partial<Record<keyof StateSnapshot['counts'], number>>;
  state_of_me: { focus: string; critical_count: number; high_count: number; has_previous_snapshot: boolean };
}

const API_BASE = '/api/state';
import { apiRequest } from './client';

export async function fetchStateSnapshot(includeExternal = true): Promise<StateSnapshot> {
  const params = new URLSearchParams({ include_external: String(includeExternal) });
  return apiRequest<StateSnapshot>(`${API_BASE}/?${params}`);
}

export async function fetchStateReport(includeExternal = true, days = 30): Promise<StateReport> {
  const params = new URLSearchParams({ include_external: String(includeExternal), days: String(days) });
  return apiRequest<StateReport>(`${API_BASE}/report?${params}`);
}
