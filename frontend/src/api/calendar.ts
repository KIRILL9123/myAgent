export interface CalendarEvent {
  uid: string;
  summary: string;
  start: string; // date or ISO datetime
  end: string;   // date or ISO datetime
  description?: string;
  commitments?: Array<{
    id: string;
    title: string;
    status: string;
    owner: string;
    deadline_at: string | null;
  }>;
}

export interface EventCreateInput {
  title: string;
  start_datetime: string;
  end_datetime?: string;
  description?: string;
  commitment_id?: string;
}

export interface EventUpdateInput {
  title?: string;
  start_datetime?: string;
  end_datetime?: string;
  description?: string;
}

const API_BASE = '/api/calendar';

export async function fetchEvents(startDate: string, endDate: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  return apiRequest<CalendarEvent[]>(`${API_BASE}/events?${params}`);
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
