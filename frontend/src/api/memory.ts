export interface FactNode {
  id: number;
  content: string;
  category: 'preference' | 'habit' | 'relationship' | 'project' | 'other';
  confidence?: number;
  // react-force-graph coordinates populated during rendering
  x?: number;
  y?: number;
}

export interface FactEdge {
  source: number | FactNode;
  target: number | FactNode;
  relation_type: 'related_to' | 'contradicts' | 'clarifies' | 'causes';
}

export interface MemoryGraphData {
  nodes: FactNode[];
  edges: FactEdge[];
}

export interface PendingFact {
  id: number;
  content: string;
  category: 'preference' | 'habit' | 'relationship' | 'project' | 'other';
  confidence: number;
  source_conversation_id: number | null;
  created_at: string;
  updated_at: string;
}

const API_BASE = 'http://localhost:8000/api/memory';

export async function fetchMemoryGraph(): Promise<MemoryGraphData> {
  const resp = await fetch(`${API_BASE}/graph`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch memory graph: ${resp.statusText}`);
  }
  return resp.json();
}

export async function fetchPendingFacts(): Promise<{ facts: PendingFact[] }> {
  const resp = await fetch(`${API_BASE}/pending`);
  if (!resp.ok) {
    throw new Error(`Failed to fetch pending facts: ${resp.statusText}`);
  }
  return resp.json();
}

export async function approveFact(factId: number): Promise<{ status: string; message: string }> {
  const resp = await fetch(`${API_BASE}/${factId}/approve`, {
    method: 'POST',
  });
  if (!resp.ok) {
    throw new Error(`Failed to approve fact: ${resp.statusText}`);
  }
  return resp.json();
}

export async function rejectFact(factId: number): Promise<{ status: string; message: string }> {
  const resp = await fetch(`${API_BASE}/${factId}/reject`, {
    method: 'POST',
  });
  if (!resp.ok) {
    throw new Error(`Failed to reject fact: ${resp.statusText}`);
  }
  return resp.json();
}

export async function backfillRelations(): Promise<{ status: string; message: string; relations_added: number }> {
  const resp = await fetch(`${API_BASE}/backfill-relations`, {
    method: 'POST',
  });
  if (!resp.ok) {
    throw new Error(`Failed to backfill relations: ${resp.statusText}`);
  }
  return resp.json();
}

export interface ConsolidationSuggestion {
  fact_ids: number[];
  source_facts: FactNode[];
  suggested_merged_content: string;
  category: 'preference' | 'habit' | 'relationship' | 'project' | 'other';
}

export async function fetchConsolidationSuggestions(): Promise<{ suggestions: ConsolidationSuggestion[] }> {
  const resp = await fetch(`${API_BASE}/consolidation-suggestions`, {
    method: 'POST',
  });
  if (!resp.ok) {
    throw new Error(`Failed to fetch consolidation suggestions: ${resp.statusText}`);
  }
  return resp.json();
}

export async function consolidateFacts(
  factIds: number[],
  mergedContent: string,
  category: string
): Promise<{ status: string; message: string; new_fact_id: number }> {
  const resp = await fetch(`${API_BASE}/consolidate`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      fact_ids: factIds,
      merged_content: mergedContent,
      category,
    }),
  });
  if (!resp.ok) {
    throw new Error(`Failed to consolidate facts: ${resp.statusText}`);
  }
  return resp.json();
}
