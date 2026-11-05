import { useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle, Archive, Bell, CalendarClock, Check, CheckCircle2, ChevronRight, Clock3, CreditCard,
  Inbox, RefreshCw, ShieldAlert, ShieldCheck, Timer, Undo2, X,
} from 'lucide-react';
import { Link } from 'react-router-dom';
import { approveRequest, rejectRequest } from '../api/approvals';
import { dismissAction, fetchActionCenter, markActionRead, markActionUnread, snoozeAction } from '../api/actions';
import type { ActionItem, ActionKind, ActionMode, ActionPriority } from '../api/actions';
import { completeCommitment, updateCommitment } from '../api/commitments';
import { Button, Card, Dialog, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui';

type KindFilter = 'all' | ActionKind;

const KIND_FILTERS: KindFilter[] = ['all', 'approval', 'commitment', 'subscription', 'finance', 'deadline', 'conflict', 'mail', 'error'];

const KIND_LABELS: Record<ActionKind, string> = {
  approval: 'Подтверждения',
  commitment: 'Обязательства',
  subscription: 'Подписки',
  finance: 'Финансы',
  deadline: 'Дедлайны',
  conflict: 'Конфликты',
  mail: 'Почта',
  error: 'Ошибки',
};

const KIND_ICONS: Record<ActionKind, typeof Bell> = {
  approval: ShieldCheck,
  commitment: CheckCircle2,
  subscription: CreditCard,
  finance: CreditCard,
  deadline: Timer,
  conflict: AlertTriangle,
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
  new: 'Новая',
  fixing: 'В работе',
};

const SOURCE_LABELS: Record<string, string> = {
  CHAT: 'Чат',
  EMAIL: 'Почта',
  CALENDAR: 'Календарь',
  COUNTDOWN: 'Дедлайны',
  FINANCE: 'Финансы',
  gmail: 'Gmail',
  ukrnet: 'ukr.net',
  ERROR_REPORTING: 'Система',
  CONFLICT_DETECTION: 'Проверка расписания',
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
  const repeatCount = item.metadata.repeat_count;
  if (typeof repeatCount === 'number' && repeatCount > 1) return `Повторений: ${repeatCount}`;

  const unreadCount = item.metadata.unread_count;
  if (typeof unreadCount === 'number') return `${unreadCount} писем`;

  const amount = item.metadata.amount;
  const currency = item.metadata.currency;
  if (typeof amount === 'number') return `${amount.toFixed(2)} ${typeof currency === 'string' ? currency : ''}`.trim();

  const owner = item.metadata.owner;
  return typeof owner === 'string' && owner ? `Ответственный: ${owner}` : null;
}

function collapseRepeatedSignals(items: ActionItem[]): ActionItem[] {
  const grouped = new Map<string, { item: ActionItem; count: number }>();
  items.forEach(item => {
    const key = item.kind === 'error' ? `${item.kind}|${item.title}|${item.summary}` : item.id;
    const current = grouped.get(key);
    if (current) current.count += 1;
    else grouped.set(key, { item, count: 1 });
  });
  return [...grouped.values()].map(({ item, count }) => count > 1 ? { ...item, metadata: { ...item.metadata, repeat_count: count } } : item);
}

function approvalIdFor(item: ActionItem): string | null {
  const approvalId = item.metadata.approval_id;
  return item.kind === 'approval' && typeof approvalId === 'string' ? approvalId : null;
}

function toDateTimeLocal(value: string | null): string {
  if (!value) return '';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '';
  const offset = date.getTimezoneOffset() * 60_000;
  return new Date(date.getTime() - offset).toISOString().slice(0, 16);
}

function ActionLifecycleControls({
  item,
  busy,
  onRead,
  onUnread,
  onSnooze,
  onDismiss,
  onComplete,
  onReschedule,
}: {
  item: ActionItem;
  busy: boolean;
  onRead: (item: ActionItem) => void;
  onUnread: (item: ActionItem) => void;
  onSnooze: (item: ActionItem, hours: number) => void;
  onDismiss: (item: ActionItem) => void;
  onComplete: (item: ActionItem) => void;
  onReschedule: (item: ActionItem, deadline: string) => void;
}) {
  const [snoozeOpen, setSnoozeOpen] = useState(false);
  const [rescheduleOpen, setRescheduleOpen] = useState(false);
  const [deadline, setDeadline] = useState(() => toDateTimeLocal(item.due_at));
  const isRead = item.interaction?.state === 'read';
  const isDismissed = item.interaction?.state === 'dismissed';
  const isSnoozed = item.interaction?.state === 'snoozed';

  return (
    <div className="border-t border-zinc-800 pt-3">
      <div className="flex flex-wrap justify-end gap-2">
        {isDismissed ? <Button onClick={() => onUnread(item)} disabled={busy}><Undo2 className="h-3.5 w-3.5" />Вернуть</Button> : isSnoozed ? <Button onClick={() => onUnread(item)} disabled={busy}><Undo2 className="h-3.5 w-3.5" />Вернуть сейчас</Button> : <>
          {item.kind === 'commitment' && <Button onClick={() => onComplete(item)} tone="success" disabled={busy}><Check className="h-3.5 w-3.5" />Готово</Button>}
          {item.kind === 'commitment' && <Button onClick={() => setRescheduleOpen(value => !value)} disabled={busy}>Перенести</Button>}
          <Button onClick={() => isRead ? onUnread(item) : onRead(item)} disabled={busy}>
            {isRead ? <Undo2 className="h-3.5 w-3.5" /> : <CheckCircle2 className="h-3.5 w-3.5" />}
            {isRead ? 'Вернуть' : 'Прочитано'}
          </Button>
          <Button onClick={() => setSnoozeOpen(value => !value)} disabled={busy}><Clock3 className="h-3.5 w-3.5" />Отложить</Button>
          <Button onClick={() => onDismiss(item)} tone="danger" disabled={busy}><Archive className="h-3.5 w-3.5" />Скрыть</Button>
        </>}
      </div>
      {snoozeOpen && (
        <div className="mt-2 flex flex-wrap justify-end gap-1.5 text-[11px]">
          {[['Через час', 1], ['Завтра', 24], ['Через неделю', 168]].map(([label, hours]) => (
            <button key={String(label)} type="button" onClick={() => onSnooze(item, Number(hours))} className="rounded-lg border border-zinc-700 px-2.5 py-1.5 text-zinc-400 transition hover:border-zinc-500 hover:text-zinc-100" disabled={busy}>{label}</button>
          ))}
        </div>
      )}
      {rescheduleOpen && (
        <div className="mt-3 flex flex-wrap items-center justify-end gap-2 rounded-xl border border-zinc-800 bg-zinc-950/30 p-2">
          <label className="text-[11px] text-zinc-500" htmlFor={`reschedule-${item.id}`}>Новый срок</label>
          <input id={`reschedule-${item.id}`} type="datetime-local" value={deadline} onChange={event => setDeadline(event.target.value)} className="min-h-9 rounded-lg border border-zinc-700 bg-zinc-900 px-2 text-xs text-zinc-200" />
          <Button onClick={() => deadline && onReschedule(item, deadline)} tone="success" disabled={busy || !deadline}>Сохранить</Button>
        </div>
      )}
    </div>
  );
}

function ActionCard({ item, onReject, onApprove, busy, onRead, onUnread, onSnooze, onDismiss, onComplete, onReschedule }: { item: ActionItem; onReject: (item: ActionItem) => void; onApprove: (item: ActionItem) => void; busy: boolean; onRead: (item: ActionItem) => void; onUnread: (item: ActionItem) => void; onSnooze: (item: ActionItem, hours: number) => void; onDismiss: (item: ActionItem) => void; onComplete: (item: ActionItem) => void; onReschedule: (item: ActionItem, deadline: string) => void }) {
  const Icon = KIND_ICONS[item.kind] || Bell;
  const target = targetFor(item);
  const due = formatDate(item.due_at);
  const source = item.source ? (SOURCE_LABELS[item.source] || item.source) : null;
  const status = STATUS_LABELS[item.status] || item.status;
  const metadata = metadataLabel(item);
  const approvalId = approvalIdFor(item);

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
        {item.interaction?.state === 'snoozed' && <span className="inline-flex items-center gap-1.5 text-cyan-300">Отложено до {formatDate(item.interaction.snoozed_until)}</span>}
        {item.interaction?.state === 'dismissed' && <span className="inline-flex items-center gap-1.5 text-zinc-500">Скрыто из внимания</span>}
        {item.reminder_due && <span className="inline-flex items-center gap-1.5 text-amber-300"><Bell className="h-3.5 w-3.5" />Напоминание наступило</span>}
        {item.requires_approval && <span className="inline-flex items-center gap-1.5 text-purple-300"><ShieldCheck className="h-3.5 w-3.5" />Нужно решение</span>}
      </div>

      {approvalId ? (
        <div className="flex flex-wrap justify-end gap-2 border-t border-zinc-800 pt-3">
          <Button onClick={() => onReject(item)} tone="danger" disabled={busy}>
            <X className="h-3.5 w-3.5" />Отклонить
          </Button>
          <Button onClick={() => onApprove(item)} tone="success" loading={busy}>
            <Check className="h-3.5 w-3.5" />Подтвердить
          </Button>
        </div>
      ) : target ? (
        <div className="flex justify-end">
          <Link to={target} className="inline-flex min-h-9 items-center gap-2 rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:border-purple-500/50 hover:text-zinc-100">
            {item.kind === 'error' ? 'Открыть журнал' : 'Открыть раздел'} <ChevronRight className="h-3.5 w-3.5" />
          </Link>
        </div>
      ) : null}
      <ActionLifecycleControls
        item={item}
        busy={busy}
        onRead={onRead}
        onUnread={onUnread}
        onSnooze={onSnooze}
        onDismiss={onDismiss}
        onComplete={onComplete}
        onReschedule={onReschedule}
      />
    </Card>
  );
}

export default function NotificationsPage() {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<ActionMode>('attention');
  const [kind, setKind] = useState<KindFilter>('all');
  const [pendingReject, setPendingReject] = useState<ActionItem | null>(null);
  const query = useQuery({ queryKey: ['action-center', mode], queryFn: () => fetchActionCenter(mode), staleTime: 15_000 });
  const actions = useMemo(
    () => collapseRepeatedSignals((query.data?.actions || []).filter(item => kind === 'all' || item.kind === kind)),
    [kind, query.data?.actions],
  );
  const kindCounts = useMemo(() => {
    const counts: Record<KindFilter, number> = { all: query.data?.actions.length || 0, approval: 0, commitment: 0, subscription: 0, finance: 0, deadline: 0, conflict: 0, mail: 0, error: 0 };
    (query.data?.actions || []).forEach(item => { counts[item.kind] += 1; });
    return counts;
  }, [query.data?.actions]);
  const visibleKindFilters = KIND_FILTERS.filter(value => value === 'all' || kindCounts[value] > 0 || kind === value);
  const resolutionMutation = useMutation({
    mutationFn: ({ id, decision }: { id: string; decision: 'approve' | 'reject' }) => decision === 'approve' ? approveRequest(id) : rejectRequest(id),
    onSuccess: () => {
      setPendingReject(null);
      queryClient.invalidateQueries({ queryKey: ['action-center'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['document-proposals'] });
    },
  });
  const interactionMutation = useMutation({
    mutationFn: ({ id, action, until }: { id: string; action: 'read' | 'unread' | 'dismiss' | 'snooze'; until?: string }) => {
      if (action === 'read') return markActionRead(id);
      if (action === 'unread') return markActionUnread(id);
      if (action === 'dismiss') return dismissAction(id);
      return snoozeAction(id, until || new Date(Date.now() + 60 * 60 * 1000).toISOString());
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['action-center'] });
      queryClient.invalidateQueries({ queryKey: ['state', 'snapshot'] });
    },
  });
  const commitmentMutation = useMutation({
    mutationFn: ({ id, action, deadline }: { id: string; action: 'complete' | 'reschedule'; deadline?: string }) => (
      action === 'complete'
        ? completeCommitment(id)
        : updateCommitment(id, { deadline_at: deadline ? new Date(deadline).toISOString() : null })
    ),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['action-center'] });
      queryClient.invalidateQueries({ queryKey: ['state', 'snapshot'] });
      queryClient.invalidateQueries({ queryKey: ['commitments'] });
    },
  });
  const approve = (item: ActionItem) => {
    const approvalId = approvalIdFor(item);
    if (approvalId) resolutionMutation.mutate({ id: approvalId, decision: 'approve' });
  };
  const confirmReject = () => {
    const approvalId = pendingReject && approvalIdFor(pendingReject);
    if (approvalId) resolutionMutation.mutate({ id: approvalId, decision: 'reject' });
  };
  const interactionBusy = interactionMutation.isPending || commitmentMutation.isPending;
  const markRead = (item: ActionItem) => interactionMutation.mutate({ id: item.id, action: 'read' });
  const markUnread = (item: ActionItem) => interactionMutation.mutate({ id: item.id, action: 'unread' });
  const snooze = (item: ActionItem, hours: number) => interactionMutation.mutate({ id: item.id, action: 'snooze', until: new Date(Date.now() + hours * 60 * 60 * 1000).toISOString() });
  const dismiss = (item: ActionItem) => interactionMutation.mutate({ id: item.id, action: 'dismiss' });
  const complete = (item: ActionItem) => { if (item.kind === 'commitment') commitmentMutation.mutate({ id: item.source_id, action: 'complete' }); };
  const reschedule = (item: ActionItem, deadline: string) => { if (item.kind === 'commitment') commitmentMutation.mutate({ id: item.source_id, action: 'reschedule', deadline }); };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <PageHeader
        icon={<Bell className="h-5 w-5 text-purple-300" />}
        title="Центр уведомлений"
        description="Всё, что требует внимания: решения, сроки, письма и ошибки"
        action={<div className="flex items-center gap-2"><Link to="/notifications/preferences" className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-900 px-3 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:border-zinc-600 hover:text-zinc-100">Настройки</Link><Button onClick={() => query.refetch()} loading={query.isFetching} aria-label="Обновить"><RefreshCw className="h-4 w-4" /></Button></div>}
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
            {visibleKindFilters.map(value => (
              <button key={value} type="button" aria-pressed={kind === value} onClick={() => setKind(value)} className={`inline-flex items-center gap-1.5 whitespace-nowrap rounded-lg border px-2.5 py-1.5 text-[11px] font-semibold transition-colors ${kind === value ? 'border-purple-500/40 bg-purple-500/10 text-purple-200' : 'border-zinc-800 text-zinc-500 hover:text-zinc-200'}`}>
                {value === 'all' ? 'Все типы' : KIND_LABELS[value]}
                <span className="text-[10px] opacity-60">{kindCounts[value]}</span>
              </button>
            ))}
          </div>
        </div>

        {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Не удалось загрузить центр уведомлений'} onRetry={() => query.refetch()} />}
        {!query.isError && (query.isLoading ? <LoadingState label="Загружаю сигналы…" /> : actions.length === 0 ? <EmptyState title={kind === 'all' ? (mode === 'attention' ? 'Срочных сигналов нет' : 'Сигналов пока нет') : 'Для этого фильтра сигналов нет'} description="Новые подтверждения, напоминания и предложения появятся здесь автоматически." /> : <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">{actions.map(item => <ActionCard key={item.id} item={item} onReject={setPendingReject} onApprove={approve} busy={interactionBusy || (resolutionMutation.isPending && approvalIdFor(item) === resolutionMutation.variables?.id)} onRead={markRead} onUnread={markUnread} onSnooze={snooze} onDismiss={dismiss} onComplete={complete} onReschedule={reschedule} />)}</div>)}

        {resolutionMutation.isError && <div className="flex items-center gap-2 text-xs text-rose-300"><ShieldAlert className="h-4 w-4" />{resolutionMutation.error instanceof Error ? resolutionMutation.error.message : 'Не удалось обработать решение'}</div>}
        {query.data && <p className="flex items-center justify-end gap-1.5 text-[11px] text-zinc-600"><Clock3 className="h-3.5 w-3.5" />Обновлено: {formatDate(query.data.generated_at)}</p>}
      </main>

      {pendingReject && <Dialog title="Отклонить предложение?" description="Оно исчезнет из центра уведомлений, а внешнее действие выполнено не будет." onClose={() => setPendingReject(null)}><div className="flex justify-end gap-2"><Button onClick={() => setPendingReject(null)}>Отмена</Button><Button tone="danger" onClick={confirmReject} loading={resolutionMutation.isPending}><X className="h-3.5 w-3.5" />Отклонить</Button></div></Dialog>}
    </div>
  );
}
