import { apiRequest } from './client';

export type DecisionStatus = 'ACTIVE' | 'REVISIT' | 'SUPERSEDED' | 'ARCHIVED';
export interface Decision { id: string; title: string; decision_text: string; rationale: string | null; alternatives: string[]; status: DecisionStatus; decided_at: string | null; review_at: string | null; source_type: string; created_at: string; updated_at: string; }

export const fetchDecisions = (query = '') => apiRequest<{ decisions: Decision[] }>(`/api/memory/decisions${query ? `?query=${encodeURIComponent(query)}` : ''}`);
export const createDecision = (input: Pick<Decision, 'title' | 'decision_text' | 'rationale' | 'alternatives' | 'review_at'>) => apiRequest<Decision>('/api/memory/decisions', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const revisitDecision = (id: string) => apiRequest<Decision>(`/api/memory/decisions/${id}/revisit`, { method: 'POST' });
