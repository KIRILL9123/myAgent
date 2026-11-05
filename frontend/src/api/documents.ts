import { apiRequest } from './client';

export const DOCUMENT_ACCEPT = '.txt,.md,.markdown,.csv,.json,.html,.htm,.xml,.pdf,.docx,.pptx,.xlsx,.png,.jpg,.jpeg,.webp,.epub';

export interface DocumentItem {
  id: number;
  original_name: string;
  stored_name: string;
  mime_type: string;
  extension: string;
  size_bytes: number;
  sha256: string;
  status: 'processing' | 'ready' | 'failed' | 'archived';
  error_message: string | null;
  extracted_chars: number;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface DocumentSearchResult {
  document_id: number;
  chunk_id: number;
  content: string;
  document_name: string;
  mime_type: string;
  created_at: string;
  score: number;
}

export type DocumentLinkType = 'commitment' | 'calendar_event' | 'subscription';

export interface DocumentLink {
  id: number;
  document_id: number;
  target_type: DocumentLinkType;
  target_id: string;
  target_label: string;
  relationship: string;
  created_by: string;
  created_at: string;
  target_path: string;
}

export interface DocumentLinkTarget {
  target_type: DocumentLinkType;
  id: string;
  label: string;
  detail: string;
  status?: string;
  target_path: string;
}

export type DocumentActionType = 'commitment' | 'calendar_event';

export interface DocumentProposalCandidate {
  candidate_id: string;
  title: string;
  evidence: string;
  deadline_at: string;
  date_label: string;
  confidence: number;
}

export interface DocumentProposal {
  id: string;
  source_id: string;
  title: string;
  summary: string;
  payload: Record<string, unknown>;
  source_channel: string;
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'FAILED';
  created_at: string;
  resolved_at: string | null;
  document_id: number;
  candidate_id: string;
  action_type: DocumentActionType;
}

export const fetchDocuments = (status = 'active') => apiRequest<{ documents: DocumentItem[] }>(`/api/documents?status=${encodeURIComponent(status)}`);
export const uploadDocument = (file: File) => { const body = new FormData(); body.append('file', file); return apiRequest<DocumentItem>('/api/documents/upload', { method: 'POST', body }); };
export const archiveDocument = (id: number) => apiRequest<{ status: string; document_id: number }>(`/api/documents/${id}/archive`, { method: 'POST' });
export const searchDocuments = (query: string) => apiRequest<{ results: DocumentSearchResult[] }>(`/api/documents/search?query=${encodeURIComponent(query)}`);
export const fetchDocumentLinks = (id: number) => apiRequest<{ links: DocumentLink[] }>(`/api/documents/${id}/links`);
export const fetchDocumentLinkTargets = () => apiRequest<{ targets: DocumentLinkTarget[] }>('/api/documents/link-targets');
export const createDocumentLink = (documentId: number, input: Pick<DocumentLink, 'target_type' | 'target_id' | 'target_label'> & { relationship?: string }) => apiRequest<DocumentLink>(`/api/documents/${documentId}/links`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const deleteDocumentLink = (documentId: number, linkId: number) => apiRequest<void>(`/api/documents/${documentId}/links/${linkId}`, { method: 'DELETE' });
export const fetchDocumentProposals = (id: number) => apiRequest<{ document_id: number; document_name: string; candidates: DocumentProposalCandidate[]; proposals: DocumentProposal[] }>(`/api/documents/${id}/proposals`);
export const createDocumentProposal = (documentId: number, candidateId: string, actionType: DocumentActionType) => apiRequest<{ status: string; proposal: DocumentProposal }>(`/api/documents/${documentId}/proposals`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ candidate_id: candidateId, action_type: actionType }) });
