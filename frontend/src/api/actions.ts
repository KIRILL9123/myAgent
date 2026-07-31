import { apiRequest } from './client';

export type ActionKind = 'approval' | 'commitment' | 'subscription' | 'deadline' | 'mail';
export type ActionPriority = 'critical' | 'high' | 'medium' | 'low';
export type ActionMode = 'attention' | 'all';

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
