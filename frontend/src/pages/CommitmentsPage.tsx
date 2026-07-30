import { useEffect, useMemo, useState } from 'react';
import { AlertCircle, Check, CheckCircle2, Clock3, Loader2, Mail, RefreshCw, ShieldCheck, X } from 'lucide-react';
import { approveCommitment, cancelCommitment, completeCommitment, fetchCommitments } from '../api/commitments';
import type { Commitment, CommitmentStatus } from '../api/commitments';

const STATUS_LABELS: Record<CommitmentStatus, string> = {
  PROPOSED: 'На подтверждении', ACTIVE: 'Активные', COMPLETED: 'Выполненные',
  CANCELLED: 'Отменённые', EXPIRED: 'Просроченные',
};

function formatDate(value: string | null): string {
  if (!value) return 'Без срока';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

function statusClass(status: CommitmentStatus): string {
  if (status === 'PROPOSED') return 'text-amber-300 bg-amber-500/10 border-amber-500/20';
  if (status === 'ACTIVE') return 'text-blue-300 bg-blue-500/10 border-blue-500/20';
  if (status === 'COMPLETED') return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20';
  return 'text-zinc-400 bg-zinc-800/60 border-zinc-700';
}

export default function CommitmentsPage() {
  const [commitments, setCommitments] = useState<Commitment[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setCommitments(await fetchCommitments(true)); }
    catch (err: any) { setError(err.message || 'Не удалось загрузить обязательства'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const proposed = useMemo(() => commitments.filter(item => item.status === 'PROPOSED'), [commitments]);
  const active = useMemo(() => commitments.filter(item => item.status === 'ACTIVE'), [commitments]);
  const history = useMemo(() => commitments.filter(item => ['COMPLETED', 'CANCELLED', 'EXPIRED'].includes(item.status)), [commitments]);

  const runAction = async (id: string, action: 'approve' | 'complete' | 'cancel') => {
    setBusyId(id);
    try {
      if (action === 'approve') await approveCommitment(id);
      if (action === 'complete') await completeCommitment(id);
      if (action === 'cancel') await cancelCommitment(id);
      await load();
    } catch (err: any) { setError(err.message || 'Не удалось изменить обязательство'); }
    finally { setBusyId(null); }
  };

  const renderCard = (item: Commitment) => (
    <article key={item.id} className="bg-zinc-900/50 border border-zinc-800 rounded-2xl p-5 flex flex-col gap-4 shadow-lg">
      <div className="flex justify-between gap-3 items-start">
        <div>
          <h2 className="text-sm font-semibold text-zinc-100 leading-relaxed">{item.title}</h2>
          {item.description && <p className="text-xs text-zinc-500 mt-2 leading-relaxed">{item.description}</p>}
        </div>
        <span className={`shrink-0 px-2 py-1 rounded-lg border text-[10px] font-bold ${statusClass(item.status)}`}>{STATUS_LABELS[item.status]}</span>
      </div>
      <div className="grid grid-cols-2 gap-3 text-[11px] text-zinc-500">
        <div className="flex items-center gap-2"><Clock3 className="h-3.5 w-3.5" />{formatDate(item.deadline_at)}</div>
        <div className="flex items-center gap-2"><Mail className="h-3.5 w-3.5" />{item.source_type}</div>
        <div className="text-zinc-600">Ответственный: {item.owner}</div>
        <div className="text-zinc-600">Уверенность: {Math.round(item.confidence * 100)}%</div>
      </div>
      <div className="flex gap-2 border-t border-zinc-800 pt-3">
        {item.status === 'PROPOSED' && <button onClick={() => runAction(item.id, 'approve')} disabled={busyId === item.id} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-emerald-600/80 hover:bg-emerald-500 text-[11px] font-semibold"><ShieldCheck className="h-3.5 w-3.5" />Подтвердить</button>}
        {item.status === 'ACTIVE' && <button onClick={() => runAction(item.id, 'complete')} disabled={busyId === item.id} className="flex items-center gap-1.5 px-3 py-2 rounded-lg bg-blue-600/80 hover:bg-blue-500 text-[11px] font-semibold"><Check className="h-3.5 w-3.5" />Выполнено</button>}
        {(item.status === 'PROPOSED' || item.status === 'ACTIVE') && <button onClick={() => runAction(item.id, 'cancel')} disabled={busyId === item.id} className="flex items-center gap-1.5 px-3 py-2 rounded-lg border border-zinc-700 hover:border-red-500/50 text-zinc-400 hover:text-red-300 text-[11px] font-semibold"><X className="h-3.5 w-3.5" />Отменить</button>}
        {busyId === item.id && <Loader2 className="h-4 w-4 animate-spin text-zinc-500 self-center" />}
      </div>
    </article>
  );

  const renderSection = (title: string, items: Commitment[], color: string, empty: string) => (
    <section><h2 className={`text-xs uppercase tracking-widest ${color} font-bold mb-3`}>{title} · {items.length}</h2>{items.length ? <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">{items.map(renderCard)}</div> : <p className="text-sm text-zinc-600 border border-dashed border-zinc-800 rounded-xl p-6">{empty}</p>}</section>
  );

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden">
      <header className="flex items-center justify-between px-6 py-4 border-b border-zinc-900 shrink-0"><div className="flex items-center gap-3"><CheckCircle2 className="h-5 w-5 text-purple-400" /><div><h1 className="text-xl font-bold">Обязательства</h1><p className="text-xs text-zinc-500 mt-1">Единый центр задач, обещаний и сроков</p></div></div><button onClick={load} className="p-2 rounded-lg text-zinc-500 hover:text-zinc-200 hover:bg-zinc-900"><RefreshCw className="h-4 w-4" /></button></header>
      <main className="flex-1 overflow-y-auto p-6 space-y-8">
        {error && <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-xs text-red-200"><AlertCircle className="h-4 w-4" />{error}</div>}
        {loading ? <div className="h-48 flex items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-purple-400" /></div> : <>{renderSection('Требуют подтверждения', proposed, 'text-amber-300', 'Новых предложений нет.')}{renderSection('Активные', active, 'text-blue-300', 'Активных обязательств нет.')}{history.length > 0 && renderSection('История', history, 'text-zinc-500', '')}</>}
      </main>
    </div>
  );
}
