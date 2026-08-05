import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowRight, CheckCircle2, Loader2, RefreshCw, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchStateSnapshot } from '../api/state';
import type { StateAlert } from '../api/state';

function alertColor(alert: StateAlert): string {
  if (alert.severity === 'critical') return 'text-rose-300';
  if (alert.severity === 'high') return 'text-amber-300';
  return 'text-zinc-400';
}

export default function PersonalStateWidget() {
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ['state', 'snapshot'], queryFn: () => fetchStateSnapshot(false), staleTime: 60_000 });
  const snapshot = query.data;

  return (
    <section className="surface-card mx-auto mb-6 max-w-5xl p-5 sm:p-6">
      <div className="flex items-start justify-between gap-4"><div className="flex items-center gap-3"><div className="dashboard-card-icon"><Sparkles className="h-4 w-4" /></div><h2 className="text-sm font-semibold text-zinc-100 sm:text-base">Текущее состояние</h2></div><button type="button" onClick={() => query.refetch()} disabled={query.isFetching} aria-label="Обновить состояние" className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-900/70 hover:text-zinc-200 disabled:opacity-50"><RefreshCw className={`h-4 w-4 ${query.isFetching ? 'animate-spin' : ''}`} /></button></div>
      {query.isLoading ? <div className="flex h-20 items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-[var(--app-accent)]" /></div> : query.isError ? <div className="mt-4 flex items-center justify-between gap-3 text-xs text-zinc-500"><span>Не удалось собрать сводку состояния.</span><button type="button" onClick={() => query.refetch()} className="text-emerald-300 hover:text-emerald-200">Повторить</button></div> : snapshot && (
        <>
          <div className="mt-5 flex items-center gap-2 text-sm font-semibold"><span className={`h-2.5 w-2.5 rounded-full ${snapshot.health === 'attention' ? 'bg-rose-400' : snapshot.health === 'watch' ? 'bg-amber-400' : 'bg-emerald-400'}`} />{snapshot.headline}</div>
          <div className="mt-4 grid grid-cols-2 gap-2 text-[11px] sm:grid-cols-4"><SummaryItem label="Обязательства" value={snapshot.counts.active_commitments} /><SummaryItem label="Подписки" value={snapshot.counts.active_subscriptions} /><SummaryItem label="Дедлайны · 30 дн." value={snapshot.counts.deadlines_next_30_days} /><SummaryItem label="Требуют внимания" value={snapshot.counts.alerts_total} /></div>
          <div className="mt-4 space-y-2">{snapshot.next_actions.length ? snapshot.next_actions.slice(0, 3).map(alert => <button type="button" key={`${alert.type}-${alert.title}`} onClick={() => alert.target && navigate(alert.target)} className="flex w-full items-center gap-2 rounded-xl border border-zinc-800/70 bg-zinc-950/20 px-3 py-2 text-left text-xs hover:border-zinc-700"><AlertTriangle className={`h-3.5 w-3.5 shrink-0 ${alertColor(alert)}`} /><span className="min-w-0 flex-1 truncate text-zinc-300">{alert.title}</span>{alert.target && <ArrowRight className="h-3.5 w-3.5 shrink-0 text-zinc-600" />}</button>) : <div className="flex items-center gap-2 text-xs text-emerald-300"><CheckCircle2 className="h-4 w-4" />Нет срочных действий</div>}</div>
          <button type="button" onClick={() => navigate('/state')} className="mt-4 flex items-center gap-1 text-xs font-semibold text-emerald-300 hover:text-emerald-200">Открыть полную сводку <ArrowRight className="h-3.5 w-3.5" /></button>
        </>
      )}
    </section>
  );
}

function SummaryItem({ label, value }: { label: string; value: number }) {
  return <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/30 p-3"><div className="text-zinc-500">{label}</div><div className="mt-1 font-mono text-zinc-200">{value}</div></div>;
}
