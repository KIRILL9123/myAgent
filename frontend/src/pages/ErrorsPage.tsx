import { useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { AlertTriangle, Check, ChevronRight, Plus, RefreshCw, ShieldAlert } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui';
import { createErrorReport, fetchErrorReports, updateErrorReport } from '../api/errors';
import type { ErrorReport, ErrorSeverity, ErrorStatus } from '../api/errors';

const STATUS_LABELS: Record<ErrorStatus, string> = { new: 'Новая', fixing: 'В работе', fixed: 'Исправлена', verified: 'Проверена', closed: 'Закрыта' };
const SEVERITY_LABELS: Record<ErrorSeverity, string> = { critical: 'Критическая', high: 'Высокая', medium: 'Средняя', low: 'Низкая' };
const STATUS_ORDER: ErrorStatus[] = ['new', 'fixing', 'fixed', 'verified', 'closed'];
const SEVERITY_STYLES: Record<ErrorSeverity, string> = {
  critical: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  high: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  medium: 'border-purple-500/30 bg-purple-500/10 text-purple-200',
  low: 'border-zinc-700 bg-zinc-800/50 text-zinc-400',
};
const STATUS_STYLES: Record<ErrorStatus, string> = {
  new: 'border-rose-500/20 bg-rose-500/5 text-rose-200',
  fixing: 'border-amber-500/20 bg-amber-500/5 text-amber-200',
  fixed: 'border-cyan-500/20 bg-cyan-500/5 text-cyan-200',
  verified: 'border-emerald-500/20 bg-emerald-500/5 text-emerald-200',
  closed: 'border-zinc-700 bg-zinc-800/50 text-zinc-400',
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

function nextStatus(status: ErrorStatus): ErrorStatus | null {
  const index = STATUS_ORDER.indexOf(status);
  return index >= 0 && index < STATUS_ORDER.length - 1 ? STATUS_ORDER[index + 1] : null;
}

function inputClass(): string {
  return 'w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-xs text-zinc-200 outline-none focus:border-purple-500/60';
}

type Draft = { fix_reference: string; verification_result: string; resolution_note: string };

function ErrorCard({ report, draft, onDraftChange, onAdvance, busy }: { report: ErrorReport; draft: Draft; onDraftChange: (draft: Draft) => void; onAdvance: () => void; busy: boolean }) {
  const upcoming = nextStatus(report.status);
  return (
    <Card className="flex flex-col gap-4 p-5">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-700 bg-zinc-800/60 text-rose-300"><AlertTriangle className="h-5 w-5" /></span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2"><h2 className="text-sm font-semibold text-zinc-100">{report.title}</h2><div className="flex gap-1.5"><span className={`rounded-lg border px-2 py-1 text-[10px] font-bold ${SEVERITY_STYLES[report.severity]}`}>{SEVERITY_LABELS[report.severity]}</span><span className={`rounded-lg border px-2 py-1 text-[10px] font-semibold ${STATUS_STYLES[report.status]}`}>{STATUS_LABELS[report.status]}</span></div></div>
          {report.summary && <p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-400">{report.summary}</p>}
        </div>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-2 border-t border-zinc-800 pt-3 text-[11px] text-zinc-500"><span>{report.component || 'Без компонента'}</span>{report.error_type && <span>{report.error_type}</span>}<span>Создана: {formatDate(report.created_at)}</span>{report.correlation_id && <span className="font-mono">{report.correlation_id}</span>}</div>
      {Object.keys(report.context).length > 0 && <div className="rounded-xl border border-zinc-800 bg-zinc-950/50 p-3 text-[11px] text-zinc-500">{Object.entries(report.context).map(([key, value]) => <div key={key} className="flex gap-2"><span className="text-zinc-600">{key}:</span><span className="break-all text-zinc-400">{String(value)}</span></div>)}</div>}
      {report.fix_reference && <p className="text-xs text-cyan-200">Исправление: {report.fix_reference}</p>}
      {report.verification_result && <p className="text-xs text-emerald-200">Проверка: {report.verification_result}</p>}
      {upcoming && <div className="space-y-3 border-t border-zinc-800 pt-3"><div className="grid gap-2 sm:grid-cols-3"><input value={draft.fix_reference} onChange={event => onDraftChange({ ...draft, fix_reference: event.target.value })} placeholder="Ссылка на исправление" className={inputClass()} /><input value={draft.verification_result} onChange={event => onDraftChange({ ...draft, verification_result: event.target.value })} placeholder="Результат проверки" className={inputClass()} /><input value={draft.resolution_note} onChange={event => onDraftChange({ ...draft, resolution_note: event.target.value })} placeholder="Комментарий" className={inputClass()} /></div><div className="flex justify-end"><Button onClick={onAdvance} loading={busy} tone={upcoming === 'closed' ? 'success' : 'neutral'}><ChevronRight className="h-3.5 w-3.5" />{STATUS_LABELS[upcoming]}</Button></div></div>}
    </Card>
  );
}

export default function ErrorsPage() {
  const queryClient = useQueryClient();
  const [status, setStatus] = useState<ErrorStatus | 'all'>('all');
  const [showForm, setShowForm] = useState(false);
  const [drafts, setDrafts] = useState<Record<number, Draft>>({});
  const [form, setForm] = useState({ title: '', summary: '', severity: 'medium' as ErrorSeverity, component: '', correlation_id: '' });
  const query = useQuery({ queryKey: ['error-reports', status], queryFn: () => fetchErrorReports(status), staleTime: 15_000 });
  const createMutation = useMutation({ mutationFn: createErrorReport, onSuccess: () => { setForm({ title: '', summary: '', severity: 'medium', component: '', correlation_id: '' }); setShowForm(false); queryClient.invalidateQueries({ queryKey: ['error-reports'] }); } });
  const updateMutation = useMutation({ mutationFn: ({ id, input }: { id: number; input: Parameters<typeof updateErrorReport>[1] }) => updateErrorReport(id, input), onSuccess: () => queryClient.invalidateQueries({ queryKey: ['error-reports'] }) });
  const reports = query.data?.reports || [];
  const summary = query.data?.summary || { new: 0, fixing: 0, fixed: 0, verified: 0, closed: 0 };
  const filters = useMemo(() => ['all', ...STATUS_ORDER] as const, []);
  const submit = (event: FormEvent) => { event.preventDefault(); if (!form.title.trim()) return; createMutation.mutate({ ...form, component: form.component || undefined, correlation_id: form.correlation_id || undefined }); };
  const draftFor = (report: ErrorReport): Draft => drafts[report.id] || { fix_reference: report.fix_reference || '', verification_result: report.verification_result || '', resolution_note: report.resolution_note || '' };

  return <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100"><PageHeader icon={<ShieldAlert className="h-5 w-5 text-rose-300" />} title="Отчёты об ошибках" description="Контекст, исправления и проверка проблем проекта" action={<div className="flex gap-2"><Button onClick={() => setShowForm(value => !value)}><Plus className="h-4 w-4" />Добавить</Button><Button onClick={() => query.refetch()} loading={query.isFetching} aria-label="Обновить"><RefreshCw className="h-4 w-4" /></Button></div>} /><main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Не удалось загрузить отчёты'} onRetry={() => query.refetch()} />}
    {createMutation.isError && <ErrorState message={createMutation.error instanceof Error ? createMutation.error.message : 'Не удалось создать отчёт'} />}
    {updateMutation.isError && <ErrorState message={updateMutation.error instanceof Error ? updateMutation.error.message : 'Не удалось обновить отчёт'} />}
    {showForm && <form onSubmit={submit} className="grid gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 sm:grid-cols-2"><input required value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} placeholder="Название ошибки" className={inputClass()} /><select value={form.severity} onChange={event => setForm({ ...form, severity: event.target.value as ErrorSeverity })} className={inputClass()}>{Object.entries(SEVERITY_LABELS).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</select><input value={form.component} onChange={event => setForm({ ...form, component: event.target.value })} placeholder="Компонент" className={inputClass()} /><input value={form.correlation_id} onChange={event => setForm({ ...form, correlation_id: event.target.value })} placeholder="Correlation ID (необязательно)" className={inputClass()} /><textarea value={form.summary} onChange={event => setForm({ ...form, summary: event.target.value })} placeholder="Что произошло и какой контекст важен" rows={3} className={`${inputClass()} sm:col-span-2`} /><div className="flex justify-end gap-2 sm:col-span-2"><Button type="button" onClick={() => setShowForm(false)}>Отмена</Button><Button type="submit" tone="primary" loading={createMutation.isPending}><Check className="h-4 w-4" />Сохранить отчёт</Button></div></form>}
    <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">{(['new', 'fixing', 'fixed', 'verified', 'closed'] as ErrorStatus[]).map(value => <Card key={value} className="p-3"><p className="text-[10px] uppercase tracking-wider text-zinc-600">{STATUS_LABELS[value]}</p><p className="mt-2 text-xl font-bold text-zinc-200">{summary[value]}</p></Card>)}</div>
    <div className="flex gap-2 overflow-x-auto pb-1">{filters.map(value => <button key={value} type="button" onClick={() => setStatus(value)} className={`whitespace-nowrap rounded-lg border px-3 py-2 text-xs font-semibold ${status === value ? 'border-purple-500/40 bg-purple-500/10 text-purple-200' : 'border-zinc-800 text-zinc-500 hover:text-zinc-200'}`}>{value === 'all' ? 'Все' : STATUS_LABELS[value]} {value !== 'all' && <span className="opacity-60">{summary[value]}</span>}</button>)}</div>
    {query.isLoading ? <LoadingState label="Загружаю отчёты…" /> : reports.length === 0 ? <EmptyState title="Отчётов нет" description="Ошибки HTTP 5xx будут создаваться автоматически, а новые отчёты можно добавить вручную." /> : <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">{reports.map(report => <ErrorCard key={report.id} report={report} draft={draftFor(report)} onDraftChange={draft => setDrafts(current => ({ ...current, [report.id]: draft }))} onAdvance={() => { const draft = draftFor(report); const upcoming = nextStatus(report.status); if (upcoming) updateMutation.mutate({ id: report.id, input: { status: upcoming, ...draft } }); }} busy={updateMutation.isPending && updateMutation.variables?.id === report.id} />)}</div>}
  </main></div>;
}
