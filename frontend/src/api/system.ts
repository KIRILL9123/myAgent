import { apiRequest } from './client';

const API_BASE = '/api/system';

export interface SystemStatus {
  overall: 'ok' | 'degraded';
  generated_at: string;
  backend: { status: string; message: string };
  llm: {
    provider: string;
    model: string;
    endpoint: string;
    status: string;
    latency_ms: number | null;
    detail: string | null;
  };
  services: Record<string, { status: string; latency_ms: number | null; detail: string | null }>;
  ports: Array<{ host: string; port: number; reachable: boolean; latency_ms: number | null }>;
  host: { platform: string; hostname: string; python: string };
  host_metrics: HostDiagnostics;
}

export interface HostDiagnostics {
  status: string;
  detail: string | null;
  generated_at: string;
  collection_latency_ms: number;
  cpu: { percent: number | null; cores: number };
  memory: { total_bytes: number | null; available_bytes: number | null; used_percent: number | null };
  disks: Array<{ name: string; total_bytes: number; free_bytes: number; used_percent: number | null }>;
  processes: Array<{ name: string; pid: number; cpu_seconds: number | null; memory_bytes: number }>;
  process_count: number | null;
}

export async function fetchSystemStatus(): Promise<SystemStatus> {
  return apiRequest<SystemStatus>(`${API_BASE}/status`);
}
