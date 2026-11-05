import { apiRequest } from './client';

export type NotificationPriority = 'critical' | 'high' | 'medium' | 'low';

export interface NotificationPreferences {
  enabled: boolean;
  timezone: string;
  quiet_hours_start: string;
  quiet_hours_end: string;
  max_messages_per_window: number;
  window_minutes: number;
  min_priority: NotificationPriority;
  coalesce_window_minutes: number;
  updated_at?: string | null;
}

export type NotificationPreferencesUpdate = Partial<Omit<NotificationPreferences, 'updated_at'>>;

export function fetchNotificationPreferences(): Promise<NotificationPreferences> {
  return apiRequest<NotificationPreferences>('/api/notifications/preferences');
}

export function updateNotificationPreferences(changes: NotificationPreferencesUpdate): Promise<NotificationPreferences> {
  return apiRequest<NotificationPreferences>('/api/notifications/preferences', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(changes),
  });
}
