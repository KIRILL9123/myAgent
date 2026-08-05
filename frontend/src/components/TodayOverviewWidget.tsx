import { AlertTriangle, ArrowRight, BellRing, CalendarDays, CheckCircle2, Clock3, RefreshCw, Sparkles } from 'lucide-react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import type { StateAlert, StateSnapshot } from '../api/state';
import { completeCommitment } from '../api/commitments';

interface TodayOverviewWidgetProps {
  snapshot?: StateSnapshot;
  isLoading: boolean;
  isError: boolean;
  isFetching: boolean;
  onRefresh: () => void;
}

const dateFormatter = new Intl.DateTimeFormat('ru-RU', {
  weekday: 'long',
  day: 'numeric',
  month: 'long',
});

function formatTime(value: string | null | undefined, allDay = false): string {
  if (!value || allDay || !value.includes('T')) return 'Весь день';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value.split('T')[1]?.slice(0, 5) || value : date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function formatDue(value: string | null): string {
  if (!value) return 'Без срока';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  const today = new Date();
  const isToday = date.toDateString() === today.toDateString();
  return isToday ? `Сегодня, ${formatTime(value)}` : date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' });
}

function severityClass(severity: StateAlert['severity']): string {
  if (severity === 'critical') return 'text-rose-300';
  if (severity === 'high') return 'text-amber-300';
  return 'text-zinc-400';
}

function SummaryMetric({ label, value, tone = 'text-zinc-100' }: { label: string; value: number; tone?: string }) {
  return (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/30 px-3 py-3">
      <div className="text-[11px] text-zinc-500">{label}</div>
      <div className={`mt-1 text-lg font-semibold ${tone}`}>{value}</div>
    </div>
  );
}

export default function TodayOverviewWidget({ snapshot, isLoading, isError, isFetching, onRefresh }: TodayOverviewWidgetProps) {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const completeMutation = useMutation({
    mutationFn: completeCommitment,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['state', 'snapshot'] });
      queryClient.invalidateQueries({ queryKey: ['action-center'] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
    },
  });
  const events = snapshot?.domains.calendar.events
    ? [...snapshot.domains.calendar.events].sort((a, b) => a.start.localeCompare(b.start))
    : [];
  const tasks = snapshot?.domains.commitments
    .filter(task => task.status === 'ACTIVE')
    .sort((a, b) => (a.deadline_at || '9999').localeCompare(b.deadline_at || '9999'))
    .slice(0, 4) || [];
  const actions = snapshot?.next_actions.slice(0, 4) || [];
  const todayLabel = dateFormatter.format(new Date());

  return (
    <section className="surface-card mx-auto mb-6 max-w-5xl p-5 sm:p-6" aria-labelledby="today-overview-title">
      <div className="flex items-start justify-between gap-4">
        <div className="flex min-w-0 items-start gap-3">
          <div className="dashboard-card-icon"><Sparkles className="h-4 w-4" /></div>
          <div className="min-w-0">
            <h2 id="today-overview-title" className="text-base font-semibold text-zinc-100">Сегодня</h2>
            <p className="mt-1 truncate text-xs capitalize text-zinc-500">{todayLabel}</p>
          </div>
        </div>
        <button type="button" onClick={onRefresh} disabled={isFetching} aria-label="Обновить обзор на сегодня" className="rounded-lg p-2 text-zinc-500 transition hover:bg-zinc-900/70 hover:text-zinc-200 disabled:opacity-50">
          <RefreshCw className={`h-4 w-4 ${isFetching ? 'animate-spin' : ''}`} />
        </button>
      </div>

      {isLoading ? (
        <div className="flex h-36 items-center justify-center text-sm text-zinc-500">Собираю сегодняшний обзор…</div>
      ) : isError || !snapshot ? (
        <div className="mt-5 flex items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-xs text-rose-200">
          <span>Не удалось собрать обзор на сегодня.</span>
          <button type="button" onClick={onRefresh} className="font-semibold text-rose-200 hover:text-white">Повторить</button>
        </div>
      ) : (
        <>
          <div className="mt-5 flex items-center gap-2 text-sm font-semibold text-zinc-200">
            <span className={`h-2.5 w-2.5 rounded-full ${snapshot.health === 'attention' ? 'bg-rose-400' : snapshot.health === 'watch' ? 'bg-amber-400' : 'bg-emerald-400'}`} />
            <span>{snapshot.headline}</span>
          </div>

          <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
            <SummaryMetric label="События сегодня" value={snapshot.counts.calendar_events_today} />
            <SummaryMetric label="Активные задачи" value={snapshot.counts.active_commitments} />
            <SummaryMetric label="Сроки · 30 дней" value={snapshot.counts.deadlines_next_30_days} />
            <SummaryMetric label="Требуют внимания" value={snapshot.counts.alerts_total} tone={snapshot.counts.alerts_total ? 'text-amber-200' : 'text-emerald-300'} />
          </div>

          <div className="mt-5 grid gap-3 lg:grid-cols-[1.2fr_0.9fr]">
            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200"><CalendarDays className="h-4 w-4 text-emerald-300" />Расписание сегодня</div>
                <button type="button" onClick={() => navigate('/calendar')} className="text-xs text-zinc-500 hover:text-zinc-200">Открыть календарь</button>
              </div>
              <div className="mt-3 space-y-1.5">
                {events.length ? events.slice(0, 5).map(event => (
                  <button type="button" key={event.uid} onClick={() => navigate('/calendar')} className="flex w-full items-center gap-3 rounded-lg px-2 py-2 text-left transition hover:bg-zinc-900/70">
                    <span className="w-14 shrink-0 text-[11px] font-medium text-zinc-500">{formatTime(event.start, event.all_day)}</span>
                    <span className="min-w-0 flex-1 truncate text-xs text-zinc-200">{event.summary}</span>
                    {event.conflicts?.length ? <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-amber-300" aria-label="Есть конфликт" /> : <ArrowRight className="h-3.5 w-3.5 shrink-0 text-zinc-700" aria-hidden="true" />}
                  </button>
                )) : (
                  <div className="flex items-center gap-2 px-2 py-4 text-xs text-zinc-500"><CheckCircle2 className="h-4 w-4 text-emerald-300" />Свободный день</div>
                )}
              </div>
            </div>

            <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/20 p-4">
              <div className="flex items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200"><BellRing className="h-4 w-4 text-amber-300" />Следующие действия</div>
                <button type="button" onClick={() => navigate('/notifications')} className="text-xs text-zinc-500 hover:text-zinc-200">Все</button>
              </div>
              <div className="mt-3 space-y-1.5">
                {actions.length ? actions.map(action => (
                  <button type="button" key={`${action.type}-${action.title}`} onClick={() => navigate(action.target || '/notifications')} className="flex w-full items-start gap-2 rounded-lg px-2 py-2 text-left transition hover:bg-zinc-900/70">
                    <AlertTriangle className={`mt-0.5 h-3.5 w-3.5 shrink-0 ${severityClass(action.severity)}`} />
                    <span className="min-w-0 flex-1"><span className="block truncate text-xs text-zinc-200">{action.title}</span><span className="mt-0.5 block truncate text-[11px] text-zinc-500">{action.detail}</span></span>
                  </button>
                )) : (
                  <div className="flex items-center gap-2 px-2 py-4 text-xs text-emerald-300"><CheckCircle2 className="h-4 w-4" />Срочных действий нет</div>
                )}
              </div>
            </div>
          </div>

          <div className="mt-3 rounded-xl border border-zinc-800/80 bg-zinc-950/20 p-4">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2 text-sm font-semibold text-zinc-200"><Clock3 className="h-4 w-4 text-zinc-400" />Ближайшие задачи</div>
              <button type="button" onClick={() => navigate('/commitments')} className="inline-flex items-center gap-1 text-xs text-zinc-500 hover:text-zinc-200">Открыть задачи <ArrowRight className="h-3.5 w-3.5" /></button>
            </div>
            <div className="mt-3 grid gap-1.5 sm:grid-cols-2">
              {tasks.length ? tasks.map(task => (
                <div key={task.id} className="flex min-w-0 items-center gap-2 rounded-lg px-2 py-2 transition hover:bg-zinc-900/70">
                  <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-300" />
                  <button type="button" onClick={() => navigate('/commitments')} className="min-w-0 flex-1 truncate text-left text-xs text-zinc-300">{task.title}</button>
                  <span className="shrink-0 text-[11px] text-zinc-600">{formatDue(task.deadline_at)}</span>
                  <button type="button" onClick={() => completeMutation.mutate(task.id)} disabled={completeMutation.isPending} aria-label={`Завершить задачу: ${task.title}`} className="rounded-md p-1 text-zinc-600 transition hover:bg-emerald-500/10 hover:text-emerald-300 disabled:opacity-50">✓</button>
                </div>
              )) : <div className="px-2 py-3 text-xs text-zinc-500">Активных задач пока нет.</div>}
            </div>
          </div>
        </>
      )}
    </section>
  );
}
