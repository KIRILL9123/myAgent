import { useEffect, useState } from 'react';
import { AlertCircle, Check, CheckCircle2, Clock3, Loader2, RefreshCw, ShieldAlert, X } from 'lucide-react';
import { approveRequest, fetchApprovals, rejectRequest } from '../api/approvals';
import type { ApprovalKind, ApprovalRequest } from '../api/approvals';

const KIND_LABELS: Record<ApprovalKind, string> = {
  FACT: 'Факт памяти', COMMITMENT: 'Обязательство', ACTION: 'Действие агента',
};
const KIND_STYLES: Record<ApprovalKind, string> = {
  FACT: 'text-purple-300 bg-purple-500/10 border-purple-500/20',
  COMMITMENT: 'text-amber-300 bg-amber-500/10 border-amber-500/20',
  ACTION: 'text-rose-300 bg-rose-500/10 border-rose-500/20',
};

function formatDate(value: string): string {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

export default function ApprovalsPage() {
  const [items, setItems] = useState<ApprovalRequest[]>([]);
  const [loading, setLoading] = useState(true);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setItems(await fetchApprovals()); }
    catch (err: any) { setError(err.message || 'Не удалось загрузить подтверждения'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const resolve = async (item: ApprovalRequest, decision: 'approve' | 'reject') => {
    if (decision === 'reject' && !window.confirm('Отклонить это предложение?')) return;
    setBusyId(item.id);
    try {
      if (decision === 'approve') await approveRequest(item.id); else await rejectRequest(item.id);
      setItems(current => current.filter(entry => entry.id !== item.id));
    } catch (err: any) { setError(err.message || 'Не удалось обработать подтверждение'); }
    finally { setBusyId(null); }
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex shrink-0 items-center justify-between border-b border-zinc-900 px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex min-w-0 items-center gap-3"><CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" /><div className="min-w-0"><h1 className="truncate text-lg font-bold sm:text-xl">Центр подтверждений</h1><p className="mt-1 truncate text-xs text-zinc-500">Единый вход для предложений и действий агента</p></div></div>
        <button onClick={load} className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200" aria-label="Обновить"><RefreshCw className="h-4 w-4" /></button>
      </header>
      <main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
        {error && <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-200"><AlertCircle className="h-4 w-4" />{error}</div>}
        <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-xs leading-relaxed text-zinc-400">Здесь собраны подтверждения памяти, обязательств и потенциально опасных действий. Ничего внешнего не выполняется без вашего решения.</div>
        {loading ? <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-emerald-400" /></div> : items.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-zinc-800 p-10 text-center"><ShieldAlert className="mx-auto h-8 w-8 text-zinc-700" /><p className="mt-3 text-sm text-zinc-500">Новых подтверждений нет</p></div>
        ) : <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">{items.map(item => (
          <article key={item.id} className="flex flex-col gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 shadow-lg">
            <div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-semibold text-zinc-100">{item.title}</h2><p className="mt-2 whitespace-pre-wrap break-words text-xs leading-relaxed text-zinc-400">{item.summary}</p></div><span className={`shrink-0 rounded-lg border px-2 py-1 text-[10px] font-bold ${KIND_STYLES[item.kind]}`}>{KIND_LABELS[item.kind]}</span></div>
            <div className="flex items-center gap-2 text-[11px] text-zinc-600"><Clock3 className="h-3.5 w-3.5" />{formatDate(item.created_at)} · {item.source_channel}</div>
            <div className="flex gap-2 border-t border-zinc-800 pt-3"><button onClick={() => resolve(item, 'reject')} disabled={busyId === item.id} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-[11px] font-semibold text-zinc-400 hover:border-rose-500/50 hover:text-rose-300 disabled:opacity-50"><X className="h-3.5 w-3.5" />Отклонить</button><button onClick={() => resolve(item, 'approve')} disabled={busyId === item.id} className="inline-flex min-h-10 items-center gap-1.5 rounded-lg bg-emerald-600/80 px-3 py-2 text-[11px] font-semibold hover:bg-emerald-500 disabled:opacity-50"><Check className="h-3.5 w-3.5" />Подтвердить</button>{busyId === item.id && <Loader2 className="h-4 w-4 animate-spin self-center text-zinc-500" />}</div>
          </article>
        ))}</div>}
      </main>
    </div>
  );
}
