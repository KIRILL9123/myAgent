import { apiRequest } from './client';

const API_BASE = '/api/approvals/';

export type ApprovalKind = 'FACT' | 'COMMITMENT' | 'SUBSCRIPTION' | 'ACTION';

export interface ApprovalRequest {
  id: string;
  kind: ApprovalKind;
  source_id: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  source_channel: string;
  status: string;
  created_at: string;
  resolved_at?: string | null;
}

export async function fetchApprovals(): Promise<ApprovalRequest[]> {
  const data = await apiRequest<{ approvals: ApprovalRequest[] }>(API_BASE);
  return data.approvals;
}

async function resolveApproval(id: string, decision: 'approve' | 'reject') {
  return apiRequest(`${API_BASE}${id}/${decision}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ note: null }),
  });
}

export const approveRequest = (id: string) => resolveApproval(id, 'approve');
export const rejectRequest = (id: string) => resolveApproval(id, 'reject');
