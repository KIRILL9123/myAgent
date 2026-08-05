export interface CalendarEvent {
  uid: string;
  summary: string;
  start: string; // date or ISO datetime
  end: string;   // date or ISO datetime
  description?: string;
  all_day?: boolean;
  recurrence?: string | null;
  recurrence_until?: string | null;
  reminder_minutes?: number | null;
  calendar_id?: string;
  calendar_name?: string;
  calendar_color?: string;
  commitments?: Array<{
    id: string;
    title: string;
    status: string;
    owner: string;
    deadline_at: string | null;
  }>;
  conflicts?: Array<{
    id: string;
    type: string;
    title: string;
    summary: string;
    priority: string;
    due_at: string | null;
    fact_id?: number | null;
    fact_content?: string | null;
    preference_rule?: { kind: string; value: string | number };
  }>;
}

export interface CalendarConflict {
  id: string;
  type: string;
  title: string;
  summary: string;
  priority: string;
  due_at: string | null;
  fact_id?: number | null;
  fact_content?: string | null;
  preference_rule?: { kind: string; value: string | number };
}

export interface CalendarConflictPayload {
  code: 'calendar_conflicts';
  message: string;
  conflicts: CalendarConflict[];
}

export interface EventCreateInput {
  title: string;
  start_datetime: string;
  end_datetime?: string;
  description?: string;
  commitment_id?: string;
  all_day?: boolean;
  recurrence?: string;
  recurrence_until?: string;
  reminder_minutes?: number | null;
  calendar_id?: string;
  allow_conflicts?: boolean;
}

export interface EventUpdateInput {
  title?: string;
  start_datetime?: string;
  end_datetime?: string;
  description?: string;
  all_day?: boolean;
  recurrence?: string;
  recurrence_until?: string;
  reminder_minutes?: number | null;
  allow_conflicts?: boolean;
}

export interface CalendarSource {
  calendar_id: string;
  calendar_name: string;
  calendar_color?: string;
}

const API_BASE = '/api/calendar';

export async function fetchEvents(startDate: string, endDate: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiRequest<CalendarEvent[]>(`${API_BASE}/events?${params}`);
}

export async function fetchCalendars(): Promise<CalendarSource[]> {
  return apiRequest<CalendarSource[]>(`${API_BASE}/calendars`);
}

export async function searchEvents(query: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams({ query });
  return apiRequest<CalendarEvent[]>(`${API_BASE}/search?${params}`);
}

export async function createEvent(input: EventCreateInput): Promise<CalendarEvent> {
  return apiRequest<CalendarEvent>(`${API_BASE}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function modifyEvent(uid: string, input: EventUpdateInput): Promise<CalendarEvent> {
  return apiRequest<CalendarEvent>(`${API_BASE}/events/${uid}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export async function deleteEvent(uid: string): Promise<{ status: string }> {
  return apiRequest<{ status: string }>(`${API_BASE}/events/${uid}`, {
    method: 'DELETE',
  });
}
import { apiRequest } from './client';
