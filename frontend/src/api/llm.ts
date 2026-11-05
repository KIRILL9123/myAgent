import { apiRequest } from './client';

export type LlmProviderId = 'local' | 'deepseek';

export interface LlmProfile {
  id: LlmProviderId;
  label: string;
  kind: string;
  active: boolean;
  configured: boolean;
  endpoint: string;
  models: { main: string; extractor: string; classifier: string };
}

export interface LlmStatus {
  active_provider: LlmProviderId;
  active_model: string;
  profiles: LlmProfile[];
  redaction_enabled: boolean;
  fallback_enabled: boolean;
}

export interface LlmCheckResult {
  provider: LlmProviderId;
  status: 'ok' | 'error' | 'not_configured';
  detail: string;
  latency_ms?: number;
}

export function fetchLlmStatus(): Promise<LlmStatus> {
  return apiRequest<LlmStatus>('/api/system/llm');
}

export function setLlmProvider(provider: LlmProviderId): Promise<LlmStatus> {
  return apiRequest<LlmStatus>('/api/system/llm/provider', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider }),
  });
}

export function setLlmModels(provider: LlmProviderId, models: Partial<LlmProfile['models']>): Promise<LlmStatus> {
  return apiRequest<LlmStatus>('/api/system/llm/models', {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ provider, ...models }),
  });
}

export function checkLlmProvider(provider: LlmProviderId): Promise<LlmCheckResult> {
  return apiRequest<LlmCheckResult>(`/api/system/llm/check?provider=${provider}`, { method: 'POST' });
}
