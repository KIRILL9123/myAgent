import { apiRequest } from './client';

export type ActionKind = 'approval' | 'commitment' | 'subscription' | 'finance' | 'deadline' | 'conflict' | 'mail' | 'error';
export type ActionPriority = 'critical' | 'high' | 'medium' | 'low';
export type ActionMode = 'attention' | 'all';
export type ActionInteractionState = 'unread' | 'read' | 'snoozed' | 'dismissed';

export interface ActionItem {
  id: string;
  kind: ActionKind;
  source_id: string;
  title: string;
  summary: string;
  status: string;
  priority: ActionPriority;
  due_at: string | null;
  reminder_at: string | null;
  reminder_due: boolean;
  source: string | null;
  target: string | null;
  requires_approval: boolean;
  interaction: {
    state: ActionInteractionState;
    snoozed_until: string | null;
    updated_at: string | null;
  };
  metadata: Record<string, unknown>;
}

export interface ActionCenterResponse {
  generated_at: string;
  timezone: string;
  mode: ActionMode;
  summary: {
    total: number;
    returned: number;
    critical: number;
    high: number;
    overdue: number;
    due_today: number;
    requires_approval: number;
    reminders_due: number;
    conflicts: number;
    unread: number;
    read: number;
  };
  actions: ActionItem[];
}

export async function fetchActionCenter(mode: ActionMode): Promise<ActionCenterResponse> {
  const params = new URLSearchParams({
    mode,
    limit: '100',
    include_external: 'true',
  });
  return apiRequest<ActionCenterResponse>(`/api/actions?${params}`);
}

export function markActionRead(actionId: string): Promise<{ action_id: string; state: ActionInteractionState }> {
  return apiRequest(`/api/actions/${encodeURIComponent(actionId)}/read`, { method: 'POST' });
}

export function markActionUnread(actionId: string): Promise<{ action_id: string; state: ActionInteractionState }> {
  return apiRequest(`/api/actions/${encodeURIComponent(actionId)}/unread`, { method: 'POST' });
}

export function snoozeAction(actionId: string, snoozedUntil: string): Promise<{ action_id: string; state: ActionInteractionState; snoozed_until: string }> {
  return apiRequest(`/api/actions/${encodeURIComponent(actionId)}/snooze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ snoozed_until: snoozedUntil }),
  });
}

export function dismissAction(actionId: string): Promise<{ action_id: string; state: ActionInteractionState }> {
  return apiRequest(`/api/actions/${encodeURIComponent(actionId)}/dismiss`, { method: 'POST' });
}
