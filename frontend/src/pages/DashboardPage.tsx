import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Calendar, 
  Wallet, 
  Clock, 
  Mail, 
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  ChevronRight
} from 'lucide-react';
import SystemStatusWidget from '../components/SystemStatusWidget';
import { fetchEvents } from '../api/calendar';
import { fetchSummary } from '../api/finance';
import { fetchCountdowns } from '../api/countdown';
import { fetchUnreadEmails } from '../api/mail';
import type { CalendarEvent } from '../api/calendar';
import type { FinanceSummary } from '../api/finance';
import PersonalStateWidget from '../components/PersonalStateWidget';

// Helper to format date as YYYY-MM-DD in local time
function getLocalDateString(d: Date = new Date()) {
  const year = d.getFullYear();
  const month = String(d.getMonth() + 1).padStart(2, '0');
  const day = String(d.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

export default function DashboardPage() {
  const navigate = useNavigate();

  // Widget States: Loading, Error, Data
  // 1. Calendar
  const [calCount, setCalCount] = useState<number>(0);
  const [firstEvent, setFirstEvent] = useState<CalendarEvent | null>(null);
  const [calLoading, setCalLoading] = useState<boolean>(true);
  const [calError, setCalError] = useState<boolean>(false);

  // 2. Finance
  const [financeSum, setFinanceSum] = useState<FinanceSummary | null>(null);
  const [finLoading, setFinLoading] = useState<boolean>(true);
  const [finError, setFinError] = useState<boolean>(false);

  // 3. Countdowns
  const [urgentCount, setUrgentCount] = useState<number>(0);
  const [cdLoading, setCdLoading] = useState<boolean>(true);
  const [cdError, setCdError] = useState<boolean>(false);

  // 4. Mail
  const [mailCount, setMailCount] = useState<number>(0);
  const [mailLoading, setMailLoading] = useState<boolean>(true);
  const [mailError, setMailError] = useState<boolean>(false);

  useEffect(() => {
    // Load Calendar
    const loadCalendar = async () => {
      setCalLoading(true);
      setCalError(false);
      try {
        const todayStr = getLocalDateString();
        const events = await fetchEvents(todayStr, todayStr);
        setCalCount(events.length);
        if (events.length > 0) {
          // Sort events by start time if available
          const sorted = [...events].sort((a, b) => a.start.localeCompare(b.start));
          setFirstEvent(sorted[0]);
        } else {
          setFirstEvent(null);
        }
      } catch (err) {
        console.error('Calendar widget error:', err);
        setCalError(true);
      } finally {
        setCalLoading(false);
      }
    };

    // Load Finance
    const loadFinance = async () => {
      setFinLoading(true);
      setFinError(false);
      try {
        const now = new Date();
        const firstDayStr = getLocalDateString(new Date(now.getFullYear(), now.getMonth(), 1));
        const lastDayStr = getLocalDateString(new Date(now.getFullYear(), now.getMonth() + 1, 0));
        const sum = await fetchSummary(firstDayStr, lastDayStr);
        setFinanceSum(sum);
      } catch (err) {
        console.error('Finance widget error:', err);
        setFinError(true);
      } finally {
        setFinLoading(false);
      }
    };

    // Load Countdowns
    const loadCountdowns = async () => {
      setCdLoading(true);
      setCdError(false);
      try {
        const countdownsList = await fetchCountdowns();
        const urgent = countdownsList.filter(c => c.days_remaining <= 30 && c.days_remaining >= 0);
        setUrgentCount(urgent.length);
      } catch (err) {
        console.error('Countdowns widget error:', err);
        setCdError(true);
      } finally {
        setCdLoading(false);
      }
    };

    // Load Mail
    const loadMail = async () => {
      setMailLoading(true);
      setMailError(false);
      try {
        // Fetch gmail and ukrnet in parallel
        const [gmail, ukrnet] = await Promise.all([
          fetchUnreadEmails('gmail').catch(() => []),
          fetchUnreadEmails('ukrnet').catch(() => [])
        ]);
        setMailCount(gmail.length + ukrnet.length);
      } catch (err) {
        console.error('Mail widget error:', err);
        setMailError(true);
      } finally {
        setMailLoading(false);
      }
    };

    loadCalendar();
    loadFinance();
    loadCountdowns();
    loadMail();
  }, []);

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(val);
  };

  const getEventTime = (event: CalendarEvent) => {
    if (!event.start) return '';
    if (event.start.includes('T')) {
      const parts = event.start.split('T')[1].split(':');
      return `${parts[0]}:${parts[1]}`;
    }
    return 'Весь день';
  };

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Обзор Системы
          </h1>
        </div>
        <div className="text-xs text-zinc-550 font-mono hidden md:block">
          Home Agent Hub v2.0
        </div>
      </header>

      {/* Main Grid View */}
      <main className="flex-1 overflow-y-auto p-4 sm:p-6">
        <SystemStatusWidget />
        <PersonalStateWidget />
        <section className="mx-auto mt-8 max-w-5xl" aria-labelledby="dashboard-domains-title">
          <div className="mb-3 flex items-end justify-between gap-3"><div><h2 id="dashboard-domains-title" className="text-xs font-bold uppercase tracking-widest text-zinc-400">Центр управления</h2><p className="mt-1 text-xs text-zinc-600">Быстрый обзор ключевых областей агента</p></div><span className="text-[10px] text-zinc-600">4 раздела</span></div>
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          
          {/* Card 1: Calendar */}
          <div 
            onClick={() => navigate('/calendar')}
            role="button" tabIndex={0} aria-label="Открыть календарь" onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') navigate('/calendar'); }} className="group bg-zinc-900/30 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all cursor-pointer flex flex-col justify-between hover:shadow-lg shadow-md min-h-[170px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sky-400/70"
          >
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="p-3 rounded-2xl bg-sky-500/10 text-sky-400 border border-sky-500/10">
                  <Calendar className="h-5 w-5" />
                </div>
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest group-hover:text-sky-400 transition-colors">
                  Календарь
                </span>
              </div>

              {calLoading ? (
                <div className="space-y-2.5 animate-pulse">
                  <div className="h-5 bg-zinc-900 rounded-lg w-1/3"></div>
                  <div className="h-3.5 bg-zinc-900 rounded-lg w-2/3"></div>
                </div>
              ) : calError ? (
                <div className="text-zinc-500 text-xs flex items-center gap-1.5 py-1">
                  <AlertTriangle className="h-4 w-4 text-zinc-650" />
                  <span>Не удалось загрузить данные</span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="text-xl font-bold font-sans tracking-tight">
                    {calCount === 0 ? 'Нет событий сегодня' : `${calCount} ${calCount % 10 === 1 && calCount % 100 !== 11 ? 'событие' : [2,3,4].includes(calCount % 10) && ![12,13,14].includes(calCount % 100) ? 'события' : 'событий'}`}
                  </div>
                  {firstEvent && (
                    <div className="text-xs text-zinc-450 truncate flex items-center gap-2">
                      <span className="font-mono text-sky-400 bg-sky-500/5 px-2 py-0.5 rounded border border-sky-500/10">
                        {getEventTime(firstEvent)}
                      </span>
                      <span className="font-medium truncate">{firstEvent.summary}</span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-between items-center border-t border-zinc-900/80 pt-4 mt-6">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 group-hover:text-zinc-350 transition-colors">
                Перейти в Календарь
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-zinc-350 transform group-hover:translate-x-1 transition-all" />
            </div>
          </div>

          {/* Card 2: Finance */}
          <div 
            onClick={() => navigate('/finance')}
            role="button" tabIndex={0} aria-label="Открыть финансы" onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') navigate('/finance'); }} className="group bg-zinc-900/30 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all cursor-pointer flex flex-col justify-between hover:shadow-lg shadow-md min-h-[170px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-emerald-400/70"
          >
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="p-3 rounded-2xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
                  <Wallet className="h-5 w-5" />
                </div>
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest group-hover:text-emerald-400 transition-colors">
                  Финансы
                </span>
              </div>

              {finLoading ? (
                <div className="space-y-2.5 animate-pulse">
                  <div className="h-5 bg-zinc-900 rounded-lg w-1/2"></div>
                  <div className="h-3.5 bg-zinc-900 rounded-lg w-2/3"></div>
                </div>
              ) : finError ? (
                <div className="text-zinc-500 text-xs flex items-center gap-1.5 py-1">
                  <AlertTriangle className="h-4 w-4 text-zinc-650" />
                  <span>Не удалось загрузить данные</span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className={`text-xl font-bold font-mono tracking-tight ${financeSum && financeSum.net_balance >= 0 ? 'text-emerald-400' : 'text-rose-450'}`}>
                    {financeSum ? formatCurrency(financeSum.net_balance) : '—'}
                  </div>
                  {financeSum && (
                    <div className="text-xs text-zinc-500 flex gap-3 font-mono">
                      <span className="flex items-center gap-1">
                        <TrendingUp className="h-3.5 w-3.5 text-emerald-500" />
                        {formatCurrency(financeSum.total_income)}
                      </span>
                      <span className="flex items-center gap-1">
                        <TrendingDown className="h-3.5 w-3.5 text-rose-500" />
                        {formatCurrency(financeSum.total_expense)}
                      </span>
                    </div>
                  )}
                </div>
              )}
            </div>

            <div className="flex justify-between items-center border-t border-zinc-900/80 pt-4 mt-6">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 group-hover:text-zinc-350 transition-colors">
                Перейти в Бюджет
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-zinc-350 transform group-hover:translate-x-1 transition-all" />
            </div>
          </div>

          {/* Card 3: Countdowns */}
          <div 
            onClick={() => navigate('/deadlines')}
            role="button" tabIndex={0} aria-label="Открыть дедлайны" onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') navigate('/deadlines'); }} className="group bg-zinc-900/30 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all cursor-pointer flex flex-col justify-between hover:shadow-lg shadow-md min-h-[170px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-rose-400/70"
          >
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="p-3 rounded-2xl bg-rose-500/10 text-rose-400 border border-rose-500/10">
                  <Clock className="h-5 w-5" />
                </div>
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest group-hover:text-rose-400 transition-colors">
                  Дедлайны
                </span>
              </div>

              {cdLoading ? (
                <div className="space-y-2.5 animate-pulse">
                  <div className="h-5 bg-zinc-900 rounded-lg w-1/3"></div>
                  <div className="h-3.5 bg-zinc-900 rounded-lg w-2/3"></div>
                </div>
              ) : cdError ? (
                <div className="text-zinc-500 text-xs flex items-center gap-1.5 py-1">
                  <AlertTriangle className="h-4 w-4 text-zinc-650" />
                  <span>Не удалось загрузить данные</span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="text-xl font-bold font-sans tracking-tight flex items-center gap-2">
                    <span>{urgentCount === 0 ? 'Нет срочных дедлайнов' : `${urgentCount} срочных`}</span>
                    {urgentCount > 0 && <span className="h-2 w-2 rounded-full bg-rose-500 animate-ping"></span>}
                  </div>
                  <div className="text-xs text-zinc-500 leading-relaxed font-sans">
                    {urgentCount === 0 
                      ? 'Все задачи в плановом режиме' 
                      : 'Требуют внимания в ближайшие 30 дней'
                    }
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center border-t border-zinc-900/80 pt-4 mt-6">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 group-hover:text-zinc-350 transition-colors">
                Перейти в Дедлайны
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-zinc-350 transform group-hover:translate-x-1 transition-all" />
            </div>
          </div>

          {/* Card 4: Mail */}
          <div 
            onClick={() => navigate('/mail')}
            role="button" tabIndex={0} aria-label="Открыть почту" onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') navigate('/mail'); }} className="group bg-zinc-900/30 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all cursor-pointer flex flex-col justify-between hover:shadow-lg shadow-md min-h-[170px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-amber-400/70"
          >
            <div>
              <div className="flex justify-between items-center mb-4">
                <div className="p-3 rounded-2xl bg-amber-500/10 text-amber-400 border border-amber-500/10">
                  <Mail className="h-5 w-5" />
                </div>
                <span className="text-[10px] font-bold text-zinc-500 uppercase tracking-widest group-hover:text-amber-400 transition-colors">
                  Почта
                </span>
              </div>

              {mailLoading ? (
                <div className="space-y-2.5 animate-pulse">
                  <div className="h-5 bg-zinc-900 rounded-lg w-1/4"></div>
                  <div className="h-3.5 bg-zinc-900 rounded-lg w-2/3"></div>
                </div>
              ) : mailError ? (
                <div className="text-zinc-500 text-xs flex items-center gap-1.5 py-1">
                  <AlertTriangle className="h-4 w-4 text-zinc-650" />
                  <span>Не удалось загрузить почту</span>
                </div>
              ) : (
                <div className="space-y-1.5">
                  <div className="text-xl font-bold font-sans tracking-tight">
                    {mailCount === 0 ? 'Нет непрочитанных' : `${mailCount} непрочитанных`}
                  </div>
                  <div className="text-xs text-zinc-500 leading-relaxed font-sans">
                    Суммарно по аккаунтам Gmail и UkrNet
                  </div>
                </div>
              )}
            </div>

            <div className="flex justify-between items-center border-t border-zinc-900/80 pt-4 mt-6">
              <span className="text-[10px] font-bold uppercase tracking-wider text-zinc-500 group-hover:text-zinc-350 transition-colors">
                Перейти во Входящие
              </span>
              <ChevronRight className="h-4 w-4 text-zinc-600 group-hover:text-zinc-350 transform group-hover:translate-x-1 transition-all" />
            </div>
          </div>

        </div></section>
      </main>
    </div>
  );
}
