import { useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Bell, CalendarClock, CheckCircle2, ChevronRight, Clock3, Settings,
  CreditCard, Inbox, RefreshCw, ShieldAlert, ShieldCheck, Timer,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { fetchActionCenter } from '../api/actions';
import type { ActionItem, ActionKind, ActionMode, ActionPriority } from '../api/actions';
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui';

type KindFilter = 'all' | ActionKind;

const KIND_FILTERS: KindFilter[] = ['all', 'approval', 'commitment', 'subscription', 'deadline', 'mail', 'error'];

const KIND_LABELS: Record<ActionKind, string> = {
  approval: 'Подтверждения',
  commitment: 'Обязательства',
  subscription: 'Подписки',
  deadline: 'Дедлайны',
  mail: 'Почта',
  error: 'Ошибки',
};

const KIND_ICONS: Record<ActionKind, typeof Bell> = {
  approval: ShieldCheck,
  commitment: CheckCircle2,
  subscription: CreditCard,
  deadline: Timer,
  mail: Inbox,
  error: ShieldAlert,
};

const PRIORITY_STYLES: Record<ActionPriority, string> = {
  critical: 'border-rose-500/30 bg-rose-500/10 text-rose-200',
  high: 'border-amber-500/30 bg-amber-500/10 text-amber-200',
  medium: 'border-purple-500/30 bg-purple-500/10 text-purple-200',
  low: 'border-zinc-700 bg-zinc-800/50 text-zinc-400',
};

const PRIORITY_LABELS: Record<ActionPriority, string> = {
  critical: 'Срочно',
  high: 'Важно',
  medium: 'На проверку',
  low: 'Плановое',
};

const STATUS_LABELS: Record<string, string> = {
  needs_approval: 'Ждёт решения',
  overdue: 'Просрочено',
  due_today: 'Сегодня',
  upcoming: 'Скоро',
  planned: 'Запланировано',
  unread: 'Непрочитано',
};

const SOURCE_LABELS: Record<string, string> = {
  CHAT: 'Чат',
  EMAIL: 'Почта',
  CALENDAR: 'Календарь',
  COUNTDOWN: 'Дедлайны',
  gmail: 'Gmail',
  ukrnet: 'ukr.net',
  ERROR_REPORTING: 'Ошибки',
};

function formatDate(value: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

function targetFor(item: ActionItem): string | null {
  return item.target && item.target.startsWith('/') ? item.target : null;
}

function metadataLabel(item: ActionItem): string | null {
  const unreadCount = item.metadata.unread_count;
  if (typeof unreadCount === 'number') return `${unreadCount} писем`;

  const amount = item.metadata.amount;
  const currency = item.metadata.currency;
  if (typeof amount === 'number') return `${amount.toFixed(2)} ${typeof currency === 'string' ? currency : ''}`.trim();

  const owner = item.metadata.owner;
  return typeof owner === 'string' && owner ? `Ответственный: ${owner}` : null;
}

function ActionCard({ item }: { item: ActionItem }) {
  const Icon = KIND_ICONS[item.kind] || Bell;
  const target = targetFor(item);
  const due = formatDate(item.due_at);
  const source = item.source ? (SOURCE_LABELS[item.source] || item.source) : null;
  const status = STATUS_LABELS[item.status] || item.status;
  const metadata = metadataLabel(item);
  return (
    <Card className="flex flex-col gap-4 p-4 sm:p-5">
      <div className="flex items-start gap-3">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl border border-zinc-700 bg-zinc-800/60 text-purple-300">
          <Icon className="h-5 w-5" />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-2">
            <h2 className="text-sm font-semibold text-zinc-100">{item.title}</h2>
            <div className="flex shrink-0 flex-wrap justify-end gap-1.5">
              <span className={`rounded-lg border px-2 py-1 text-[10px] font-bold ${PRIORITY_STYLES[item.priority]}`}>
                {PRIORITY_LABELS[item.priority]}
              </span>
              {status && <span className="rounded-lg border border-zinc-700 bg-zinc-900 px-2 py-1 text-[10px] font-semibold text-zinc-400">{status}</span>}
            </div>
          </div>
          <p className="mt-2 text-xs leading-relaxed text-zinc-400">{item.summary}</p>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-4 gap-y-2 border-t border-zinc-800 pt-3 text-[11px] text-zinc-500">
        <span className="inline-flex items-center gap-1.5"><span className="text-zinc-600">Тип:</span>{KIND_LABELS[item.kind]}</span>
        {source && <span className="inline-flex items-center gap-1.5"><span className="text-zinc-600">Источник:</span>{source}</span>}
        {due && <span className="inline-flex items-center gap-1.5"><CalendarClock className="h-3.5 w-3.5 text-zinc-600" />{due}</span>}
        {metadata && <span className="inline-flex items-center gap-1.5 text-zinc-400">{metadata}</span>}
        {item.reminder_due && <span className="inline-flex items-center gap-1.5 text-amber-300"><Bell className="h-3.5 w-3.5" />Напоминание наступило</span>}
        {item.requires_approval && <span className="inline-flex items-center gap-1.5 text-purple-300"><ShieldCheck className="h-3.5 w-3.5" />Нужно решение</span>}
      </div>

      {target && (
        <div className="flex justify-end">
          <Link to={target} className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:border-purple-500/50 hover:text-zinc-100">
            Открыть раздел <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      )}
    </Card>
  );
}

export default function NotificationsPage() {
  const [mode, setMode] = useState<ActionMode>('attention');
  const [kind, setKind] = useState<KindFilter>('all');
  const query = useQuery({ queryKey: ['action-center', mode], queryFn: () => fetchActionCenter(mode), staleTime: 15_000 });
  const actions = useMemo(
    () => (query.data?.actions || []).filter(item => kind === 'all' || item.kind === kind),
    [kind, query.data?.actions],
  );
  const kindCounts = useMemo(() => {
    const counts: Record<KindFilter, number> = { all: query.data?.actions.length || 0, approval: 0, commitment: 0, subscription: 0, deadline: 0, mail: 0, error: 0 };
    (query.data?.actions || []).forEach(item => { counts[item.kind] += 1; });
    return counts;
  }, [query.data?.actions]);

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <PageHeader
        icon={<Bell className="h-5 w-5 text-purple-300" />}
        title="Центр уведомлений"
        description="Подтверждения, напоминания и сигналы в одном месте"
        action={<div className="flex items-center gap-2"><Link to="/notifications/preferences" className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:border-zinc-600 hover:text-zinc-100"><Settings className="h-4 w-4" />Настройки</Link><Button onClick={() => query.refetch()} loading={query.isFetching} aria-label="Обновить"><RefreshCw className="h-4 w-4" /></Button></div>}
      />
      <main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
        <section className="grid grid-cols-2 gap-3 sm:grid-cols-4" aria-label="Сводка уведомлений">
          {[
            ['Требуют решения', query.data?.summary.requires_approval ?? 0, 'text-purple-300'],
            ['Срочные', query.data?.summary.critical ?? 0, 'text-rose-300'],
            ['На сегодня', query.data?.summary.due_today ?? 0, 'text-amber-300'],
            ['Напоминания', query.data?.summary.reminders_due ?? 0, 'text-cyan-300'],
          ].map(([label, value, color]) => (
            <Card key={String(label)} className="p-3 sm:p-4">
              <p className="text-[10px] font-semibold uppercase tracking-wider text-zinc-600">{label}</p>
              <p className={`mt-2 text-xl font-bold ${color}`}>{value}</p>
            </Card>
          ))}
        </section>

        <div className="flex flex-col gap-3 rounded-2xl border border-zinc-800 bg-zinc-900/30 p-3 sm:flex-row sm:items-center sm:justify-between">
          <div className="flex rounded-xl bg-zinc-900 p-1" role="tablist" aria-label="Режим уведомлений">
            {([['attention', 'Требуют внимания'], ['all', 'Все сигналы']] as const).map(([value, label]) => (
              <button key={value} type="button" role="tab" aria-selected={mode === value} onClick={() => setMode(value)} className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${mode === value ? 'bg-purple-600 text-white' : 'text-zinc-500 hover:text-zinc-200'}`}>
                {label}
              </button>
            ))}
          </div>
          <div className="flex min-w-0 gap-2 overflow-x-auto pb-0.5" aria-label="Фильтр по типу">
            {KIND_FILTERS.map(value => (
              <button key={value} type="button" aria-pressed={kind === value} onClick={() => setKind(value)} className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold transition-colors ${kind === value ? 'border-purple-500/40 bg-purple-500/10 text-purple-200' : 'border-zinc-800 text-zinc-500 hover:text-zinc-200'}`}>
                {value === 'all' ? 'Все типы' : KIND_LABELS[value]}
                <span className="text-[10px] opacity-60">{kindCounts[value]}</span>
              </button>
            ))}
          </div>
        </div>

    {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Не удалось загрузить центр уведомлений'} onRetry={() => query.refetch()} />}
        {!query.isError && (query.isLoading ? <LoadingState label="Загружаю сигналы…" /> : actions.length === 0 ? <EmptyState title={kind === 'all' ? (mode === 'attention' ? 'Срочных сигналов нет' : 'Сигналов пока нет') : 'Для этого фильтра сигналов нет'} description="Новые подтверждения, напоминания и предложения появятся здесь автоматически." /> : <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">{actions.map(item => <ActionCard key={item.id} item={item} />)}</div>)}

        {query.data && <p className="flex items-center justify-end gap-1.5 text-[11px] text-zinc-600"><Clock3 className="h-3.5 w-3.5" />Обновлено: {formatDate(query.data.generated_at)}</p>}
      </main>
    </div>
  );
}
