import { useQuery } from '@tanstack/react-query';
import { AlertTriangle, ArrowUpRight, Calendar, CheckCircle2, Clock3, Mail, TrendingDown, TrendingUp, WalletCards } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import type { ReactNode } from 'react';
import SystemStatusWidget from '../components/SystemStatusWidget';
import TodayOverviewWidget from '../components/TodayOverviewWidget';
import { fetchStateSnapshot } from '../api/state';
import type { CalendarEvent } from '../api/calendar';
import type { StateSnapshot } from '../api/state';

function formatCurrency(value: number) {
  return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(value);
}

function getEventTime(event: CalendarEvent) {
  if (!event.start || event.all_day || !event.start.includes('T')) return 'Весь день';
  const date = new Date(event.start);
  return Number.isNaN(date.getTime()) ? event.start.split('T')[1]?.slice(0, 5) || event.start : date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' });
}

function eventCountLabel(value: number) {
  if (value === 0) return 'Нет событий сегодня';
  if (value % 10 === 1 && value % 100 !== 11) return `${value} событие`;
  if ([2, 3, 4].includes(value % 10) && ![12, 13, 14].includes(value % 100)) return `${value} события`;
  return `${value} событий`;
}

function MetricCard({ icon, label, value, detail, footer, onClick }: { icon: ReactNode; label: string; value: string; detail?: ReactNode; footer: string; onClick: () => void }) {
  return (
    <button type="button" className="dashboard-card" onClick={onClick}>
      <div>
        <div className="dashboard-card-top"><span className="dashboard-card-icon">{icon}</span><span className="dashboard-card-label">{label}</span></div>
        <div className="dashboard-card-value">{value}</div>
        <div className="dashboard-card-detail">{detail}</div>
      </div>
      <div className="dashboard-card-footer"><span>{footer}</span><ArrowUpRight className="h-4 w-4" aria-hidden="true" /></div>
    </button>
  );
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const snapshotQuery = useQuery<StateSnapshot>({
    queryKey: ['state', 'snapshot'],
    queryFn: () => fetchStateSnapshot(false),
    staleTime: 60_000,
  });
  const snapshot = snapshotQuery.data;
  const events = snapshot?.domains.calendar.events ? [...snapshot.domains.calendar.events].sort((a, b) => a.start.localeCompare(b.start)) : [];
  const firstEvent: CalendarEvent | null = events[0] ?? null;
  const calCount = snapshot?.counts.calendar_events_today ?? 0;
  const financeSum = snapshot?.domains.finance;
  const urgentCount = snapshot?.counts.deadlines_next_30_days ?? 0;
  const mailCount = snapshot?.counts.unread_emails ?? 0;
  const calError = snapshotQuery.isError || snapshot?.domains.calendar.status === 'error';
  const mailError = snapshot?.domains.mail.status === 'error';
  const loadingValue = (value: string) => snapshotQuery.isLoading ? '…' : snapshotQuery.isError ? '—' : value;

  return (
    <div className="page-shell">
      <header className="page-header"><div className="page-header-title"><span className="page-header-icon"><CheckCircle2 className="h-4 w-4" /></span><div><h1>Главная</h1><p>Спокойный обзор того, что требует внимания</p></div></div></header>
      <main className="page-content">
        <div className="dashboard-intro"><h2>Что важно сегодня</h2></div>

        <div className="mx-auto max-w-[1160px] space-y-6">
          <SystemStatusWidget />
          <TodayOverviewWidget
            snapshot={snapshot}
            isLoading={snapshotQuery.isLoading}
            isError={snapshotQuery.isError}
            isFetching={snapshotQuery.isFetching}
            onRefresh={() => { void snapshotQuery.refetch(); }}
          />
          <section aria-labelledby="dashboard-domains-title">
            <div className="mb-3 flex items-center justify-between"><h2 id="dashboard-domains-title" className="text-xs font-semibold text-zinc-400">Рабочая область</h2><span className="text-[11px] text-zinc-600">Обновляется автоматически</span></div>
            <div className="dashboard-grid">
              <MetricCard icon={<Calendar className="h-4 w-4" />} label="Календарь" value={loadingValue(eventCountLabel(calCount))} detail={calError ? <span className="inline-flex items-center gap-1.5"><AlertTriangle className="h-3.5 w-3.5" />Не удалось загрузить</span> : firstEvent ? <span><strong className="font-medium text-zinc-300">{getEventTime(firstEvent)}</strong> · {firstEvent.summary}</span> : 'День свободен'} footer="Открыть календарь" onClick={() => navigate('/calendar')} />
              <MetricCard icon={<WalletCards className="h-4 w-4" />} label="Финансы" value={loadingValue(financeSum ? formatCurrency(financeSum.net_balance) : '—')} detail={financeSum && !snapshotQuery.isError ? <span className="inline-flex items-center gap-3"><span className="inline-flex items-center gap-1"><TrendingUp className="h-3.5 w-3.5 text-emerald-400" />{formatCurrency(financeSum.total_income)}</span><span className="inline-flex items-center gap-1"><TrendingDown className="h-3.5 w-3.5 text-rose-300" />{formatCurrency(financeSum.total_expense)}</span></span> : snapshotQuery.isError ? 'Не удалось загрузить' : 'Баланс за текущий месяц'} footer="Открыть финансы" onClick={() => navigate('/finance')} />
              <MetricCard icon={<Clock3 className="h-4 w-4" />} label="Дедлайны" value={loadingValue(urgentCount === 0 ? 'Всё спокойно' : `${urgentCount} требуют внимания`)} detail={snapshotQuery.isError ? 'Не удалось загрузить' : urgentCount === 0 ? 'Нет срочных сроков в ближайшие 30 дней' : 'Проверьте ближайшие сроки'} footer="Открыть дедлайны" onClick={() => navigate('/deadlines')} />
              <MetricCard icon={<Mail className="h-4 w-4" />} label="Почта" value={loadingValue(mailCount === 0 ? 'Всё прочитано' : `${mailCount} непрочитанных`)} detail={mailError ? 'Не удалось загрузить почту' : 'Gmail и UkrNet'} footer="Открыть входящие" onClick={() => navigate('/mail')} />
            </div>
          </section>
        </div>
      </main>
    </div>
  );
}
