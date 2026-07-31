import { apiRequest } from './client';

export type FactCategory = 'preference' | 'habit' | 'relationship' | 'project' | 'other';
export interface FactNode { id: number; content: string; category: FactCategory; confidence?: number; x?: number; y?: number; }
export interface FactEdge { source: number | FactNode; target: number | FactNode; relation_type: 'related_to' | 'contradicts' | 'clarifies' | 'causes'; }
export interface MemoryGraphData { nodes: FactNode[]; edges: FactEdge[]; }
export interface PendingFact extends FactNode { confidence: number; source_conversation_id: number | null; created_at: string; updated_at: string; }
export interface MemoryFact extends FactNode { confidence: number; status: string; source_conversation_id: number | null; created_at: string; updated_at: string; last_confirmed_at: string | null; valid_from: string | null; valid_to: string | null; source_type: string; approval_mode: string; provenance: Record<string, unknown>; is_pinned: boolean; }
export interface MemoryNote { id: number; title: string; content: string; tags: string[]; status: 'active' | 'archived'; created_at: string; updated_at: string; }
export interface MemoryOverview { notes: number; approved_facts: number; pending_facts: number; stale_facts: number; }
export type SkillStatus = 'draft' | 'approved' | 'disabled';
export interface ProceduralSkill { id: number; name: string; description: string; triggers: string[]; steps: string[]; category: string; source: 'builtin' | 'user'; status: SkillStatus; version: number; use_count: number; last_used_at: string | null; created_at: string; updated_at: string; approval_id?: string; }
export interface ConsolidationSuggestion { fact_ids: number[]; source_facts: FactNode[]; suggested_merged_content: string; category: FactCategory; }
const API_BASE = '/api/memory';

export const fetchMemoryGraph = () => apiRequest<MemoryGraphData>(`${API_BASE}/graph`);
export const fetchPendingFacts = () => apiRequest<{ facts: PendingFact[] }>(`${API_BASE}/pending`);
export const approveFact = (factId: number) => apiRequest<{ status: string; message: string }>(`${API_BASE}/${factId}/approve`, { method: 'POST' });
export const rejectFact = (factId: number) => apiRequest<{ status: string; message: string }>(`${API_BASE}/${factId}/reject`, { method: 'POST' });
export const backfillRelations = () => apiRequest<{ status: string; message: string; relations_added: number }>(`${API_BASE}/backfill-relations`, { method: 'POST' });
export const fetchConsolidationSuggestions = () => apiRequest<{ suggestions: ConsolidationSuggestion[] }>(`${API_BASE}/consolidation-suggestions`, { method: 'POST' });
export const consolidateFacts = (factIds: number[], mergedContent: string, category: string) => apiRequest<{ status: string; message: string; new_fact_id: number }>(`${API_BASE}/consolidate`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ fact_ids: factIds, merged_content: mergedContent, category }) });
export const fetchMemoryOverview = () => apiRequest<MemoryOverview>(`${API_BASE}/overview`);
export const fetchNotes = (query = '', status = 'active') => apiRequest<{ notes: MemoryNote[] }>(`${API_BASE}/notes?${new URLSearchParams({ query, status })}`);
export const createNote = (input: { title: string; content: string; tags: string[] }) => apiRequest<MemoryNote>(`${API_BASE}/notes`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const updateNote = (id: number, input: Partial<Pick<MemoryNote, 'title' | 'content' | 'tags' | 'status'>>) => apiRequest<MemoryNote>(`${API_BASE}/notes/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const extractNoteFacts = (id: number) => apiRequest<{ facts: Array<{ id: number; status: string }> }>(`${API_BASE}/notes/${id}/extract`, { method: 'POST' });
export const fetchFacts = (query = '', category = '', status = 'approved') => apiRequest<{ facts: MemoryFact[] }>(`${API_BASE}/facts?${new URLSearchParams({ query, category, status })}`);
export const updateFact = (id: number, input: { content?: string; category?: FactCategory; is_pinned?: boolean }) => apiRequest<MemoryFact>(`${API_BASE}/facts/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const confirmFact = (id: number) => apiRequest<MemoryFact>(`${API_BASE}/facts/${id}/confirm`, { method: 'POST' });
export const setFactValidity = (id: number, valid_to: string | null) => apiRequest(`${API_BASE}/facts/${id}/validity`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ valid_to }) });
export const searchMemory = (query: string) => apiRequest<{ results: Array<{ type: 'fact' | 'note'; item: MemoryFact | MemoryNote }> }>(`${API_BASE}/search?${new URLSearchParams({ query })}`);
export const fetchSkills = (status = 'all') => apiRequest<{ skills: ProceduralSkill[] }>(`${API_BASE}/skills?${new URLSearchParams({ status })}`);
export const createSkill = (input: Pick<ProceduralSkill, 'name' | 'description' | 'triggers' | 'steps' | 'category'>) => apiRequest<ProceduralSkill>(`${API_BASE}/skills`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const disableSkill = (id: number) => apiRequest<{ status: string; skill_id: number }>(`${API_BASE}/skills/${id}/disable`, { method: 'POST' });
