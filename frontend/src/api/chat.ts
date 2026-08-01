import { apiRequest } from './client';

const API_BASE = '/api';

export interface ChatResponse {
  response: string;
  tool_calls: string[];
  requires_confirmation: boolean;
  weather?: WeatherData | null;
  web_sources?: WebSource[] | null;
  memory_used?: Array<{ type: 'fact' | 'note'; id: number; title: string }> | null;
  documents_used?: Array<{ document_id: number; document_name: string; chunk_id: number }> | null;
}

export interface WebSource {
  title: string;
  url: string;
  snippet?: string;
  method?: string;
  retrieved_at?: string;
}

export interface WeatherData {
  status: 'success';
  location: { name: string; country: string; timezone: string };
  current: {
    observed_at: string;
    temperature_c: number;
    apparent_temperature_c: number;
    precipitation_mm: number;
    wind_speed_kmh: number;
    condition: string;
    weather_code: number;
  };
  daily: Array<{
    date: string;
    condition: string;
    temperature_min_c: number;
    temperature_max_c: number;
    precipitation_probability_percent: number;
    weather_code: number;
  }>;
  source: { provider: string; retrieved_at: string };
}

export interface ChatHistoryMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  created_at?: string;
}

export function generateSessionId(): string {
  if (typeof self !== 'undefined' && self.crypto && self.crypto.randomUUID) {
    return self.crypto.randomUUID();
  }
  return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    const v = c === 'x' ? r : (r & 0x3) | 0x8;
    return v.toString(16);
  });
}

export async function sendChatMessage(message: string, sessionId: string): Promise<ChatResponse> {
  return apiRequest<ChatResponse>(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
    }),
  });
}

export async function fetchChatHistory(sessionId: string): Promise<{ history: ChatHistoryMessage[] }> {
  return apiRequest<{ history: ChatHistoryMessage[] }>(`${API_BASE}/history/${sessionId}`);
}
