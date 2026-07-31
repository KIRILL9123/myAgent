import { apiRequest } from './client';

const API_BASE = '/api/sandbox';

export interface SandboxFile { path: string; type: 'file' | 'directory'; size: number; }
export interface SandboxSnapshot { status: string; session_id: string; workspace: string; files: SandboxFile[]; total_bytes: number; limits: Record<string, number>; runtime: { configured_runtime: string; ready: boolean; message: string; security?: string; }; }
export interface SandboxCheckResult { status: string; check: string; path: string; return_code?: number; stdout?: string; stderr?: string; message?: string; duration_ms?: number; }
export interface SandboxDiffFile { path: string; status: 'added' | 'modified' | 'removed'; diff: string; additions: number; deletions: number; }
export interface SandboxDiff { status: string; session_id: string; baseline_at: string; summary: { added: number; modified: number; removed: number; changed_files: number; }; files: SandboxDiffFile[]; }
export interface SandboxApplyRequest { status: string; approval_id: string; kind: string; session_id: string; summary: Record<string, number>; message: string; }

export const fetchSandbox = (sessionId: string) => apiRequest<SandboxSnapshot>(`${API_BASE}/${encodeURIComponent(sessionId)}`);
export const fetchSandboxFile = (sessionId: string, path: string) => apiRequest<{ content: string }>(`${API_BASE}/${encodeURIComponent(sessionId)}/file?${new URLSearchParams({ path })}`);
export const writeSandboxFile = (sessionId: string, input: { path: string; content: string; overwrite: boolean }) => apiRequest<{ status: string }>(`${API_BASE}/${encodeURIComponent(sessionId)}/files`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const runSandboxCheck = (sessionId: string, input: { check: 'python' | 'pytest' | 'node' | 'compile_python'; path: string; timeout_seconds: number }) => apiRequest<SandboxCheckResult>(`${API_BASE}/${encodeURIComponent(sessionId)}/checks`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(input) });
export const fetchSandboxDiff = (sessionId: string) => apiRequest<SandboxDiff>(`${API_BASE}/${encodeURIComponent(sessionId)}/diff`);
export const captureSandboxBaseline = (sessionId: string) => apiRequest<{ status: string; baseline_at: string; file_count: number; message: string }>(`${API_BASE}/${encodeURIComponent(sessionId)}/baseline`, { method: 'POST' });
export const deleteSandboxFile = (sessionId: string, path: string) => apiRequest<{ status: string }>(`${API_BASE}/${encodeURIComponent(sessionId)}/file?${new URLSearchParams({ path })}`, { method: 'DELETE' });
export const requestSandboxApply = (sessionId: string) => apiRequest<SandboxApplyRequest>(`${API_BASE}/${encodeURIComponent(sessionId)}/apply`, { method: 'POST' });
