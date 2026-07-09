export interface CalendarEvent {
  uid: string;
  summary: string;
  start: string; // date or ISO datetime
  end: string;   // date or ISO datetime
  description?: string;
}

export interface EventCreateInput {
  title: string;
  start_datetime: string;
  end_datetime?: string;
  description?: string;
}

export interface EventUpdateInput {
  title?: string;
  start_datetime?: string;
  end_datetime?: string;
  description?: string;
}

const API_BASE = 'http://localhost:8000/api/calendar';

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

export async function fetchEvents(startDate: string, endDate: string): Promise<CalendarEvent[]> {
  const params = new URLSearchParams({ start_date: startDate, end_date: endDate });
  const resp = await fetch(`${API_BASE}/events?${params.toString()}`, {
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to fetch events: ${resp.statusText}`);
  }
  return resp.json();
}

export async function createEvent(input: EventCreateInput): Promise<CalendarEvent> {
  const resp = await fetch(`${API_BASE}/events`, {
    method: 'POST',
    headers: getHeaders(true),
    body: JSON.stringify(input),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to create event: ${resp.statusText}`);
  }
  return resp.json();
}

export async function modifyEvent(uid: string, input: EventUpdateInput): Promise<CalendarEvent> {
  const resp = await fetch(`${API_BASE}/events/${uid}`, {
    method: 'PUT',
    headers: getHeaders(true),
    body: JSON.stringify(input),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to modify event: ${resp.statusText}`);
  }
  return resp.json();
}

export async function deleteEvent(uid: string): Promise<{ status: string }> {
  const resp = await fetch(`${API_BASE}/events/${uid}`, {
    method: 'DELETE',
    headers: getHeaders(),
  });
  if (!resp.ok) {
    const errorText = await resp.text();
    throw new Error(errorText || `Failed to delete event: ${resp.statusText}`);
  }
  return resp.json();
}
