import { apiRequest } from './client';

export type ErrorStatus = 'new' | 'fixing' | 'fixed' | 'verified' | 'closed';
export type ErrorSeverity = 'critical' | 'high' | 'medium' | 'low';

export interface ErrorReport {
  id: number;
  title: string;
  summary: string;
  severity: ErrorSeverity;
  status: ErrorStatus;
  component: string | null;
  correlation_id: string | null;
  error_type: string | null;
  context: Record<string, string | number | boolean | null>;
  fix_reference: string | null;
  verification_result: string | null;
  resolution_note: string | null;
  created_at: string;
  updated_at: string;
  resolved_at: string | null;
}

export interface ErrorReportsResponse {
  reports: ErrorReport[];
  summary: Record<ErrorStatus, number>;
}

export interface ErrorReportCreateInput {
  title: string;
  summary?: string;
  severity?: ErrorSeverity;
  component?: string;
  correlation_id?: string;
  error_type?: string;
  context?: Record<string, unknown>;
}

export interface ErrorReportUpdateInput {
  status: ErrorStatus;
  fix_reference?: string;
  verification_result?: string;
  resolution_note?: string;
}

export function fetchErrorReports(status = 'all'): Promise<ErrorReportsResponse> {
  return apiRequest<ErrorReportsResponse>(`/api/errors?status=${encodeURIComponent(status)}&limit=200`);
}

export function createErrorReport(input: ErrorReportCreateInput): Promise<ErrorReport> {
  return apiRequest<ErrorReport>('/api/errors', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}

export function updateErrorReport(id: number, input: ErrorReportUpdateInput): Promise<ErrorReport> {
  return apiRequest<ErrorReport>(`/api/errors/${id}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(input),
  });
}
