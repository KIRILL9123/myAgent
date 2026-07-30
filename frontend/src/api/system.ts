const API_BASE = '/api/system';

const getHeaders = () => ({
  'X-API-Key': (import.meta.env.VITE_API_KEY as string) || '',
});

export interface SystemStatus {
  overall: 'ok' | 'degraded';
  generated_at: string;
  backend: { status: string; message: string };
  llm: { provider: string; model: string; endpoint: string; status: string; latency_ms: number | null; detail: string | null };
  services: Record<string, { status: string; latency_ms: number | null; detail: string | null }>;
  ports: Array<{ host: string; port: number; reachable: boolean; latency_ms: number | null }>;
  host: { platform: string; hostname: string; python: string };
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  const response = await fetch(`${API_BASE}/status`, { headers: getHeaders() });
  if (!response.ok) throw new Error(`Failed to fetch system status: ${response.statusText}`);
  return response.json();
}
