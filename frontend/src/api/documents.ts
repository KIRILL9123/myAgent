import { apiRequest } from './client';

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

export const fetchDocuments = (status = 'active') => apiRequest<{ documents: DocumentItem[] }>(`/api/documents?status=${encodeURIComponent(status)}`);
export const uploadDocument = (file: File) => { const body = new FormData(); body.append('file', file); return apiRequest<DocumentItem>('/api/documents/upload', { method: 'POST', body }); };
export const archiveDocument = (id: number) => apiRequest<{ status: string; document_id: number }>(`/api/documents/${id}/archive`, { method: 'POST' });
export const searchDocuments = (query: string) => apiRequest<{ results: DocumentSearchResult[] }>(`/api/documents/search?query=${encodeURIComponent(query)}`);
