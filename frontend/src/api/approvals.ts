const API_BASE = '/api/approvals/';

const getHeaders = () => ({
  'X-API-Key': (import.meta.env.VITE_API_KEY as string) || '',
});

export type ApprovalKind = 'FACT' | 'COMMITMENT' | 'ACTION';

export interface ApprovalRequest {
  id: string;
  kind: ApprovalKind;
  source_id: string;
  title: string;
  summary: string;
  payload: Record<string, any>;
  source_channel: string;
  status: string;
  created_at: string;
  resolved_at?: string | null;
}

export async function fetchApprovals(): Promise<ApprovalRequest[]> {
  const response = await fetch(API_BASE, { headers: getHeaders() });
  if (!response.ok) throw new Error(`Failed to fetch approvals: ${response.statusText}`);
  const data = await response.json();
  return data.approvals;
}

async function resolveApproval(id: string, decision: 'approve' | 'reject') {
  const response = await fetch(`${API_BASE}${id}/${decision}`, {
    method: 'POST',
    headers: { ...getHeaders(), 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: null }),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `Failed to ${decision} approval`);
  }
  return response.json();
}

export const approveRequest = (id: string) => resolveApproval(id, 'approve');
export const rejectRequest = (id: string) => resolveApproval(id, 'reject');
