import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowRight, CheckCircle2, RefreshCw, Sparkles } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { fetchStateReport } from '../api/state';
import type { StateAlert, StateReport } from '../api/state';
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui';

function formatDate(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

function severityClass(severity: StateAlert['severity']): string {
  if (severity === 'critical') return 'border-rose-500/25 bg-rose-500/10 text-rose-200';
  if (severity === 'high') return 'border-amber-500/25 bg-amber-500/10 text-amber-200';
  return 'border-zinc-800 bg-zinc-900/50 text-zinc-300';
}

function formatEuro(value: number): string { return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(value); }

function StateContent({ snapshot }: { snapshot: StateReport }) {
  const navigate = useNavigate();
  return <div className="mx-auto max-w-6xl space-y-5">
    <Card className="border-purple-500/20 bg-gradient-to-br from-purple-500/10 via-zinc-900/50 to-zinc-900/30 p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-3"><div className="flex items-center gap-2 text-sm font-semibold"><span className={`h-2.5 w-2.5 rounded-full ${snapshot.health === 'attention' ? 'bg-rose-400' : snapshot.health === 'watch' ? 'bg-amber-400' : 'bg-emerald-400'}`} />{snapshot.headline}</div><span className="text-[11px] text-zinc-600">Обновлено {formatDate(snapshot.generated_at)}</span></div>
      <div className="mt-5 grid grid-cols-2 gap-3 sm:grid-cols-4">{[['Обязательства', snapshot.counts.active_commitments], ['Подписки', snapshot.counts.active_subscriptions], ['Дедлайны · 30 дн.', snapshot.counts.deadlines_next_30_days], ['Требуют внимания', snapshot.counts.alerts_total]].map(([label, value]) => <div key={String(label)} className="rounded-xl border border-zinc-800/80 bg-zinc-950/30 p-3"><div className="text-xs text-zinc-500">{label}</div><div className="mt-1 text-xl font-bold text-zinc-100">{value}</div></div>)}</div>
    </Card>
    <section><div className="mb-3 flex items-center justify-between"><h2 className="text-xs font-bold uppercase tracking-widest text-zinc-400">Следующие действия · {snapshot.next_actions.length}</h2><span className="text-[11px] text-zinc-600">Календарь: {snapshot.domains.calendar.status} · Почта: {snapshot.domains.mail.status}</span></div>{snapshot.next_actions.length ? <div className="space-y-2">{snapshot.next_actions.map(alert => <button key={`${alert.type}-${alert.title}`} onClick={() => alert.target && navigate(alert.target)} className={`flex w-full items-start gap-3 rounded-xl border p-4 text-left transition-colors hover:border-zinc-600 ${severityClass(alert.severity)}`}><AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" /><span className="min-w-0 flex-1"><span className="block text-sm font-semibold">{alert.title}</span><span className="mt-1 block text-xs opacity-70">{alert.detail}{alert.due_at ? ` · ${formatDate(alert.due_at)}` : ''}</span></span>{alert.target && <ArrowRight className="mt-0.5 h-4 w-4 shrink-0 opacity-60" />}</button>)}</div> : <div className="flex items-center gap-2 rounded-xl border border-emerald-500/15 bg-emerald-500/5 p-5 text-sm text-emerald-300"><CheckCircle2 className="h-4 w-4" />Критичных действий сейчас нет.</div>}</section>
    <div className="grid grid-cols-1 gap-5 lg:grid-cols-2"><Card className="p-5"><h2 className="text-sm font-semibold">State of Me</h2><p className="mt-2 text-sm text-zinc-300">{snapshot.state_of_me.focus}</p><div className="mt-4 grid grid-cols-2 gap-3 text-xs text-zinc-500 sm:grid-cols-4"><span>Критичных <strong className="ml-1 text-rose-300">{snapshot.state_of_me.critical_count}</strong></span><span>Высокий приоритет <strong className="ml-1 text-amber-300">{snapshot.state_of_me.high_count}</strong></span><span>Изменений <strong className="ml-1 text-zinc-200">{Object.values(snapshot.changes).filter(value => value !== 0).length}</strong></span><span>История <strong className="ml-1 text-zinc-200">{snapshot.history.length} дн.</strong></span></div></Card><Card className="p-5"><h2 className="text-sm font-semibold">Финансы за месяц</h2><div className="mt-4 text-2xl font-bold text-emerald-300">{formatEuro(snapshot.domains.finance.net_balance)}</div><p className="mt-2 text-xs text-zinc-500">Доходы: {formatEuro(snapshot.domains.finance.total_income)} · Расходы: {formatEuro(snapshot.domains.finance.total_expense)}</p></Card></div>
    <section><h2 className="mb-3 text-xs font-bold uppercase tracking-widest text-zinc-400">История состояния</h2>{snapshot.history.length ? <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">{snapshot.history.slice(0, 9).map(item => <Card key={item.snapshot_date} className="p-3"><div className="flex justify-between text-xs"><span>{item.snapshot_date}</span><span className={item.health === 'attention' ? 'text-rose-300' : item.health === 'watch' ? 'text-amber-300' : 'text-emerald-300'}>{item.health}</span></div><div className="mt-2 truncate text-[11px] text-zinc-500">{item.headline}</div></Card>)}</div> : <EmptyState title="История ещё не сформирована" description="Снимки появятся после ежедневного запуска процессора состояния." />}</section>
  </div>;
}

export default function StatePage() {
  const query = useQuery({ queryKey: ['state', 'report', 'local'], queryFn: () => fetchStateReport(false), staleTime: 60_000 });
  return <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100"><PageHeader icon={<Sparkles className="h-5 w-5" />} title="Текущее состояние" description="Единая картина по делам, деньгам, почте и срокам" action={<Button onClick={() => query.refetch()} loading={query.isFetching} aria-label="Обновить"><RefreshCw className="h-4 w-4" /></Button>} /><main className="flex-1 overflow-y-auto p-4 sm:p-6">{query.isLoading ? <LoadingState label="Собираю состояние…" /> : query.isError ? <ErrorState message={query.error instanceof Error ? query.error.message : 'Не удалось собрать состояние'} onRetry={() => query.refetch()} /> : query.data ? <StateContent snapshot={query.data} /> : null}</main></div>;
}
