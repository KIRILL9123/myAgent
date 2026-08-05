import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  AlertCircle,
  Calendar as CalendarIcon,
  CalendarDays,
  Check,
  ChevronLeft,
  ChevronRight,
  Plus,
  RefreshCw,
  Search,
  Trash2,
  X,
} from 'lucide-react';
import { createEvent, deleteEvent, fetchCalendars, fetchEvents, modifyEvent, searchEvents } from '../api/calendar';
import type { CalendarConflict, CalendarConflictPayload, CalendarEvent, CalendarSource, EventCreateInput, EventUpdateInput } from '../api/calendar';
import { ApiError } from '../api/client';
import { createCountdown, deleteCountdown, fetchCountdowns } from '../api/countdown';
import type { Countdown } from '../api/countdown';
import { Button, Card, Dialog, ErrorState, LoadingState, PageHeader } from '../components/ui';
import CalendarView from '../components/CalendarView';

type CalendarRange = 'today' | 'week' | 'month';
type Recurrence = 'none' | 'daily' | 'weekly' | 'monthly' | 'yearly';

interface EventFormState {
  uid?: string;
  title: string;
  date: string;
  endDate: string;
  startTime: string;
  endTime: string;
  allDay: boolean;
  description: string;
  recurrence: Recurrence;
  recurrenceUntil: string;
  reminderMinutes: string;
  calendarId: string;
}

interface CountdownFormState {
  title: string;
  targetDate: string;
  category: string;
}

const WEEKDAYS = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const CALENDAR_STALE_TIME = 5 * 60 * 1000;
const SOURCE_COLORS = ['#38bdf8', '#34d399', '#fbbf24', '#c084fc', '#fb7185', '#2dd4bf'];

function formatLocalDate(date: Date) {
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
}

function parseEventDate(value: string) {
  return new Date(value.replace(' ', 'T'));
}

function getWeekStart(date: Date) {
  const monday = new Date(date);
  monday.setDate(date.getDate() - (date.getDay() === 0 ? 6 : date.getDay() - 1));
  monday.setHours(0, 0, 0, 0);
  return monday;
}

function getRangeDates(range: CalendarRange, anchorDate: Date): { start: string; end: string } {
  if (range === 'today') {
    const value = formatLocalDate(anchorDate);
    return { start: `${value}T00:00:00`, end: `${value}T23:59:59` };
  }

  if (range === 'week') {
    const monday = getWeekStart(anchorDate);
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    return { start: `${formatLocalDate(monday)}T00:00:00`, end: `${formatLocalDate(sunday)}T23:59:59` };
  }

  const first = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
  const last = new Date(anchorDate.getFullYear(), anchorDate.getMonth() + 1, 0);
  return { start: `${formatLocalDate(first)}T00:00:00`, end: `${formatLocalDate(last)}T23:59:59` };
}

function formatPeriodLabel(range: CalendarRange, anchorDate: Date): string {
  if (range === 'today') {
    return anchorDate.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  }
  if (range === 'month') {
    return anchorDate.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' });
  }
  const monday = getWeekStart(anchorDate);
  const sunday = new Date(monday);
  sunday.setDate(monday.getDate() + 6);
  return `${monday.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short' })} — ${sunday.toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' })}`;
}

function shiftAnchor(range: CalendarRange, anchorDate: Date, direction: number) {
  const next = new Date(anchorDate);
  if (range === 'today') next.setDate(next.getDate() + direction);
  else if (range === 'week') next.setDate(next.getDate() + direction * 7);
  else next.setMonth(next.getMonth() + direction);
  return next;
}

function getEventDateKey(value: string) {
  return value.replace(' ', 'T').slice(0, 10);
}

function getMonthDays(anchorDate: Date) {
  const first = new Date(anchorDate.getFullYear(), anchorDate.getMonth(), 1);
  const daysInMonth = new Date(anchorDate.getFullYear(), anchorDate.getMonth() + 1, 0).getDate();
  const leadingDays = (first.getDay() + 6) % 7;
  const totalDays = Math.ceil((leadingDays + daysInMonth) / 7) * 7;
  return Array.from({ length: totalDays }, (_, index) => {
    const day = new Date(first);
    day.setDate(index - leadingDays + 1);
    return day;
  });
}

function defaultForm(date = new Date()): EventFormState {
  const value = formatLocalDate(date);
  return {
    title: '', date: value, endDate: value, startTime: '12:00', endTime: '13:00', allDay: false,
    description: '', recurrence: 'none', recurrenceUntil: '', reminderMinutes: '', calendarId: '',
  };
}

function defaultCountdownForm(): CountdownFormState {
  return { title: '', targetDate: formatLocalDate(new Date()), category: 'личное' };
}

function formatCountdownDate(value: string) {
  const date = new Date(`${value}T00:00:00`);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
}

function eventToForm(event: CalendarEvent): EventFormState {
  const parse = (value: string) => {
    const [date = '', time = ''] = value.split(/[T ]/);
    return { date, time: time.slice(0, 5) || '00:00' };
  };
  const start = parse(event.start);
  const end = parse(event.end);
  let endDate = end.date || start.date;
  if (event.all_day && endDate) {
    const inclusiveEnd = new Date(`${endDate}T00:00:00`);
    inclusiveEnd.setDate(inclusiveEnd.getDate() - 1);
    endDate = formatLocalDate(inclusiveEnd);
  }
  return {
    uid: event.uid,
    title: event.summary,
    date: start.date || formatLocalDate(new Date()),
    endDate,
    startTime: start.time,
    endTime: end.time || '13:00',
    allDay: Boolean(event.all_day),
    description: event.description || '',
    recurrence: (event.recurrence as Recurrence) || 'none',
    recurrenceUntil: event.recurrence_until || '',
    reminderMinutes: event.reminder_minutes == null ? '' : String(event.reminder_minutes),
    calendarId: event.calendar_id || '',
  };
}

function sourceColor(sourceName: string | undefined, sourceColorValue?: string) {
  if (sourceColorValue && /^#[0-9a-f]{6}$/i.test(sourceColorValue)) return sourceColorValue;
  const hash = [...(sourceName || 'Mira')].reduce((total, character) => total + character.charCodeAt(0), 0);
  return SOURCE_COLORS[hash % SOURCE_COLORS.length];
}

function getCalendarConflictPayload(error: unknown): CalendarConflictPayload | null {
  if (!(error instanceof ApiError) || error.status !== 409 || !error.data || typeof error.data !== 'object') return null;
  const payload = error.data as Partial<CalendarConflictPayload>;
  return payload.code === 'calendar_conflicts' && Array.isArray(payload.conflicts) ? payload as CalendarConflictPayload : null;
}

export default function CalendarPage() {
  const [range, setRange] = useState<CalendarRange>('week');
  const [anchorDate, setAnchorDate] = useState(() => new Date());
  const [form, setForm] = useState<EventFormState | null>(null);
  const [pendingDelete, setPendingDelete] = useState<CalendarEvent | null>(null);
  const [periodPickerOpen, setPeriodPickerOpen] = useState(false);
  const [sourcePickerOpen, setSourcePickerOpen] = useState(false);
  const [pickerMonth, setPickerMonth] = useState(() => new Date());
  const [searchTerm, setSearchTerm] = useState('');
  const [hiddenCalendars, setHiddenCalendars] = useState<string[]>([]);
  const [countdownForm, setCountdownForm] = useState<CountdownFormState | null>(null);
  const [pendingCountdownDelete, setPendingCountdownDelete] = useState<Countdown | null>(null);
  const [pendingConflict, setPendingConflict] = useState<{ form: EventFormState; conflicts: CalendarConflict[] } | null>(null);
  const queryClient = useQueryClient();
  const dates = useMemo(() => getRangeDates(range, anchorDate), [range, anchorDate]);
  const eventsQuery = useQuery({
    queryKey: ['calendar', 'events', range, dates.start, dates.end],
    queryFn: () => fetchEvents(dates.start, dates.end),
    staleTime: CALENDAR_STALE_TIME,
    gcTime: 15 * 60 * 1000,
    select: events => [...events].sort((a, b) => parseEventDate(a.start).getTime() - parseEventDate(b.start).getTime()),
  });
  const sourcesQuery = useQuery({ queryKey: ['calendar', 'sources'], queryFn: fetchCalendars, staleTime: CALENDAR_STALE_TIME });
  const searchQuery = useQuery({
    queryKey: ['calendar', 'search', searchTerm],
    queryFn: () => searchEvents(searchTerm),
    enabled: periodPickerOpen && searchTerm.trim().length >= 2,
    staleTime: CALENDAR_STALE_TIME,
  });
  const countdownsQuery = useQuery({ queryKey: ['countdowns'], queryFn: fetchCountdowns, staleTime: CALENDAR_STALE_TIME });

  useEffect(() => {
    const prefetchMonths = async () => {
      await Promise.all(Array.from({ length: 3 }, (_, offset) => {
        const month = new Date(anchorDate);
        month.setMonth(month.getMonth() + offset);
        const monthDates = getRangeDates('month', month);
        return queryClient.prefetchQuery({
          queryKey: ['calendar', 'events', 'month', monthDates.start, monthDates.end],
          queryFn: () => fetchEvents(monthDates.start, monthDates.end),
          staleTime: CALENDAR_STALE_TIME,
        });
      }));
    };
    void prefetchMonths().catch(() => undefined);
  }, [anchorDate, queryClient]);

  const saveMutation = useMutation({
    mutationFn: ({ value, allowConflicts = false }: { value: EventFormState; allowConflicts?: boolean }) => {
      const payload = {
        title: value.title.trim(),
        start_datetime: value.allDay ? value.date : `${value.date}T${value.startTime}:00`,
        end_datetime: value.allDay ? value.endDate : `${value.date}T${value.endTime}:00`,
        description: value.description.trim() || undefined,
        all_day: value.allDay,
        recurrence: value.recurrence === 'none' ? undefined : value.recurrence,
        recurrence_until: value.recurrenceUntil || undefined,
        reminder_minutes: value.reminderMinutes === '' ? null : Number(value.reminderMinutes),
        calendar_id: value.calendarId || undefined,
        allow_conflicts: allowConflicts,
      };
      return value.uid ? modifyEvent(value.uid, payload as EventUpdateInput) : createEvent(payload as EventCreateInput);
    },
    onSuccess: () => {
      setPendingConflict(null);
      setForm(null);
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
    },
    onError: (error, variables) => {
      const conflictPayload = getCalendarConflictPayload(error);
      if (conflictPayload) setPendingConflict({ form: variables.value, conflicts: conflictPayload.conflicts });
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (uid: string) => deleteEvent(uid),
    onSuccess: () => {
      setPendingDelete(null);
      setForm(null);
      queryClient.invalidateQueries({ queryKey: ['calendar', 'events'] });
    },
  });

  const createCountdownMutation = useMutation({
    mutationFn: (value: CountdownFormState) => createCountdown({ title: value.title.trim(), target_date: value.targetDate, category: value.category.trim() || 'личное' }),
    onSuccess: () => {
      setCountdownForm(null);
      queryClient.invalidateQueries({ queryKey: ['countdowns'] });
    },
  });
  const deleteCountdownMutation = useMutation({
    mutationFn: (id: number) => deleteCountdown(id),
    onSuccess: () => {
      setPendingCountdownDelete(null);
      queryClient.invalidateQueries({ queryKey: ['countdowns'] });
    },
  });

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (form?.title.trim() && (form.allDay ? form.endDate >= form.date : form.endTime > form.startTime)) saveMutation.mutate({ value: form });
  };

  const mutationError = saveMutation.error || deleteMutation.error;
  const events = (eventsQuery.data ?? []).filter(event => !event.calendar_id || !hiddenCalendars.includes(event.calendar_id));
  const sources = sourcesQuery.data ?? [];

  const chooseDate = (date: Date) => {
    setAnchorDate(range === 'month' ? new Date(date.getFullYear(), date.getMonth(), 1) : date);
    setPeriodPickerOpen(false);
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <PageHeader
        icon={<CalendarIcon className="h-5 w-5 text-sky-400" />}
        title="Расписание и календарь"
        description="События из подключённых календарей"
        action={<Button onClick={() => eventsQuery.refetch()} loading={eventsQuery.isFetching} aria-label="Обновить календарь"><RefreshCw className="h-4 w-4" /></Button>}
      />

      <main className="flex-1 overflow-y-auto p-4 sm:p-6">
        <div className="mx-auto max-w-7xl space-y-5">
          <div className="flex flex-col justify-between gap-3 lg:flex-row lg:items-center">
            <div className="flex flex-wrap items-center gap-3">
              <div className="grid grid-cols-3 rounded-xl border border-zinc-800 bg-zinc-900/70 p-1">
                <RangeButton active={range === 'today'} onClick={() => { setRange('today'); setAnchorDate(new Date()); }}>Сегодня</RangeButton>
                <RangeButton active={range === 'week'} onClick={() => setRange('week')}>Неделя</RangeButton>
                <RangeButton active={range === 'month'} onClick={() => setRange('month')}>Месяц</RangeButton>
              </div>

              <div className="relative flex items-center gap-1 rounded-xl border border-zinc-800 bg-zinc-900/70 p-1">
                <Button onClick={() => setAnchorDate(shiftAnchor(range, anchorDate, -1))} aria-label="Предыдущий период"><ChevronLeft className="h-4 w-4" /></Button>
                <button
                  type="button"
                  onClick={() => { setPickerMonth(anchorDate); setPeriodPickerOpen(value => !value); setSourcePickerOpen(false); }}
                  className="min-w-48 rounded-lg px-3 py-2 text-center text-xs font-semibold capitalize text-zinc-300 transition-colors hover:bg-zinc-800 hover:text-zinc-100"
                  aria-expanded={periodPickerOpen}
                  aria-label="Выбрать дату или период"
                >{formatPeriodLabel(range, anchorDate)}</button>
                <Button onClick={() => setAnchorDate(shiftAnchor(range, anchorDate, 1))} aria-label="Следующий период"><ChevronRight className="h-4 w-4" /></Button>

                {periodPickerOpen && <PeriodPicker anchorDate={anchorDate} pickerMonth={pickerMonth} range={range} searchTerm={searchTerm} searchQuery={searchQuery} onMonthChange={setPickerMonth} onChooseDate={chooseDate} onSearchTermChange={setSearchTerm} onClose={() => setPeriodPickerOpen(false)} />}
              </div>

              {sources.length > 0 && <div className="relative">
                <Button onClick={() => { setSourcePickerOpen(value => !value); setPeriodPickerOpen(false); }} aria-expanded={sourcePickerOpen}>
                  <CalendarDays className="h-4 w-4" />Календари
                </Button>
                {sourcePickerOpen && <SourcePicker sources={sources} hiddenCalendars={hiddenCalendars} onToggle={calendarId => setHiddenCalendars(current => current.includes(calendarId) ? current.filter(item => item !== calendarId) : [...current, calendarId])} onClose={() => setSourcePickerOpen(false)} />}
              </div>}
            </div>

            <Button tone="primary" onClick={() => setForm(defaultForm())}><Plus className="h-4 w-4" />Добавить событие</Button>
          </div>

          {mutationError && <div className="flex items-center gap-2 rounded-xl border border-rose-500/20 bg-rose-500/5 p-3 text-xs text-rose-200"><AlertCircle className="h-4 w-4" />{mutationError instanceof Error ? mutationError.message : 'Не удалось сохранить изменения'}</div>}

          <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
            <div className="min-w-0">
              {eventsQuery.isLoading ? <LoadingState label="Загружаю календарь…" /> : eventsQuery.isError ? <ErrorState message={eventsQuery.error instanceof Error ? eventsQuery.error.message : 'Не удалось загрузить календарь'} onRetry={() => eventsQuery.refetch()} /> : <CalendarView range={range} anchorDate={anchorDate} events={events} onEdit={event => setForm(eventToForm(event))} onCreate={date => setForm(defaultForm(date))} />}
            </div>
            <CountdownPanel countdowns={countdownsQuery.data ?? []} loading={countdownsQuery.isLoading} error={countdownsQuery.error} onCreate={() => setCountdownForm(defaultCountdownForm())} onDelete={setPendingCountdownDelete} />
          </div>
        </div>
      </main>

      {form && <Dialog title={form.uid ? 'Редактировать событие' : 'Новое событие'} description={form.uid ? 'Измените параметры события.' : 'Событие появится в подключённом календаре.'} onClose={() => setForm(null)}>
        <form onSubmit={submit} className="space-y-4">
          <Field label="Название"><input required autoFocus value={form.title} onChange={event => setForm({ ...form, title: event.target.value })} className="input" placeholder="Например: День рождения Иры" /></Field>
          <label className="flex cursor-pointer items-center gap-2 text-xs font-semibold text-zinc-300"><input type="checkbox" checked={form.allDay} onChange={event => setForm({ ...form, allDay: event.target.checked })} className="h-4 w-4 accent-emerald-500" />Событие на весь день</label>
          <div className="grid grid-cols-2 gap-3">
            <Field label="Дата начала"><input required type="date" value={form.date} onChange={event => setForm({ ...form, date: event.target.value })} className="input" /></Field>
            <Field label={form.allDay ? 'Дата окончания' : 'Дата'}><input required type="date" value={form.endDate} min={form.date} onChange={event => setForm({ ...form, endDate: event.target.value })} className="input" /></Field>
          </div>
          {!form.allDay && <div className="grid grid-cols-2 gap-3"><Field label="Начало"><input required type="time" value={form.startTime} onChange={event => setForm({ ...form, startTime: event.target.value })} className="input" /></Field><Field label="Окончание"><input required type="time" value={form.endTime} onChange={event => setForm({ ...form, endTime: event.target.value })} className="input" /></Field></div>}
          <div className="grid grid-cols-2 gap-3">
            <Field label="Повтор"><select value={form.recurrence} onChange={event => setForm({ ...form, recurrence: event.target.value as Recurrence })} className="input"><option value="none">Не повторять</option><option value="daily">Каждый день</option><option value="weekly">Каждую неделю</option><option value="monthly">Каждый месяц</option><option value="yearly">Каждый год</option></select></Field>
            {form.recurrence !== 'none' ? <Field label="Повторять до"><input type="date" value={form.recurrenceUntil} onChange={event => setForm({ ...form, recurrenceUntil: event.target.value })} className="input" /></Field> : <Field label="Напомнить"><select value={form.reminderMinutes} onChange={event => setForm({ ...form, reminderMinutes: event.target.value })} className="input"><option value="">Без напоминания</option><option value="0">В момент события</option><option value="5">За 5 минут</option><option value="15">За 15 минут</option><option value="30">За 30 минут</option><option value="60">За 1 час</option><option value="1440">За 1 день</option></select></Field>}
          </div>
          {form.recurrence !== 'none' && <Field label="Напомнить"><select value={form.reminderMinutes} onChange={event => setForm({ ...form, reminderMinutes: event.target.value })} className="input"><option value="">Без напоминания</option><option value="0">В момент события</option><option value="15">За 15 минут</option><option value="60">За 1 час</option><option value="1440">За 1 день</option></select></Field>}
          {sources.length > 0 && <Field label="Календарь"><select value={form.calendarId} onChange={event => setForm({ ...form, calendarId: event.target.value })} className="input"><option value="">Основной календарь</option>{sources.map(source => <option key={source.calendar_id} value={source.calendar_id}>{source.calendar_name}</option>)}</select></Field>}
          <Field label="Описание"><textarea rows={3} value={form.description} onChange={event => setForm({ ...form, description: event.target.value })} className="input resize-none" placeholder="Детали события…" /></Field>
          <div className="flex items-center justify-between gap-2">
            <div>{form.uid && <Button type="button" tone="danger" onClick={() => setPendingDelete({ uid: form.uid!, summary: form.title, start: form.date, end: form.endDate })}><Trash2 className="h-4 w-4" />Удалить</Button>}</div>
            <div className="flex gap-2"><Button type="button" onClick={() => setForm(null)}>Отмена</Button><Button type="submit" tone="primary" loading={saveMutation.isPending}>{form.uid ? 'Сохранить' : 'Создать'}</Button></div>
          </div>
        </form>
      </Dialog>}

      {pendingConflict && <Dialog title="В календаре есть конфликт" description="Mira ничего не меняет сама. Проверьте предупреждение и решите, сохранять ли событие." onClose={() => setPendingConflict(null)}>
        <div className="space-y-3">
          {pendingConflict.conflicts.map(conflict => <div key={conflict.id} className="rounded-xl border border-amber-500/20 bg-amber-500/5 p-3 text-xs text-amber-100">
            <p className="font-semibold">{conflict.summary}</p>
            {conflict.fact_content && <p className="mt-2 text-amber-200/70">Правило из Memory: «{conflict.fact_content}»</p>}
          </div>)}
          <div className="flex justify-end gap-2 pt-2"><Button onClick={() => setPendingConflict(null)}>Отмена</Button><Button tone="primary" onClick={() => { const value = pendingConflict.form; setPendingConflict(null); saveMutation.mutate({ value, allowConflicts: true }); }} loading={saveMutation.isPending}>Сохранить всё равно</Button></div>
        </div>
      </Dialog>}

      {pendingDelete && <Dialog title="Удалить событие?" description={`«${pendingDelete.summary}» будет удалено из календаря.`} onClose={() => setPendingDelete(null)}><div className="flex justify-end gap-2"><Button onClick={() => setPendingDelete(null)}>Отмена</Button><Button tone="danger" onClick={() => deleteMutation.mutate(pendingDelete.uid)} loading={deleteMutation.isPending}>Удалить</Button></div></Dialog>}
      {countdownForm && <Dialog title="Новый дедлайн" description="Дедлайн появится рядом с календарём и будет доступен в центре уведомлений." onClose={() => setCountdownForm(null)}><form onSubmit={event => { event.preventDefault(); if (countdownForm.title.trim()) createCountdownMutation.mutate(countdownForm); }} className="space-y-4"><Field label="Название"><input required autoFocus value={countdownForm.title} onChange={event => setCountdownForm({ ...countdownForm, title: event.target.value })} className="input" placeholder="Например: DHL Erste Tag" /></Field><div className="grid grid-cols-2 gap-3"><Field label="Дата"><input required type="date" value={countdownForm.targetDate} onChange={event => setCountdownForm({ ...countdownForm, targetDate: event.target.value })} className="input" /></Field><Field label="Категория"><input value={countdownForm.category} onChange={event => setCountdownForm({ ...countdownForm, category: event.target.value })} className="input" placeholder="личное" /></Field></div>{createCountdownMutation.isError && <p className="text-xs text-rose-300">{createCountdownMutation.error instanceof Error ? createCountdownMutation.error.message : 'Не удалось создать дедлайн'}</p>}<div className="flex justify-end gap-2"><Button type="button" onClick={() => setCountdownForm(null)}>Отмена</Button><Button type="submit" tone="primary" loading={createCountdownMutation.isPending}>Создать дедлайн</Button></div></form></Dialog>}
      {pendingCountdownDelete && <Dialog title="Удалить дедлайн?" description={`«${pendingCountdownDelete.title}» будет удалён из списка.`} onClose={() => setPendingCountdownDelete(null)}><div className="flex justify-end gap-2"><Button onClick={() => setPendingCountdownDelete(null)}>Отмена</Button><Button tone="danger" onClick={() => deleteCountdownMutation.mutate(pendingCountdownDelete.id)} loading={deleteCountdownMutation.isPending}>Удалить</Button></div></Dialog>}
    </div>
  );
}

function CountdownPanel({ countdowns, loading, error, onCreate, onDelete }: { countdowns: Countdown[]; loading: boolean; error: Error | null; onCreate: () => void; onDelete: (countdown: Countdown) => void }) {
  const sorted = [...countdowns].sort((a, b) => a.target_date.localeCompare(b.target_date));
  return <Card className="h-fit p-4 sm:p-5"><div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-semibold text-zinc-100">Дедлайны</h2><p className="mt-1 text-xs text-zinc-500">Важные даты рядом с расписанием</p></div><Button onClick={onCreate} aria-label="Добавить дедлайн"><Plus className="h-4 w-4" /></Button></div>{error && <p className="mt-4 text-xs text-rose-300">{error instanceof Error ? error.message : 'Не удалось загрузить дедлайны'}</p>}{loading ? <div className="mt-5"><LoadingState label="Загружаю…" /></div> : sorted.length === 0 ? <div className="mt-5 rounded-xl border border-dashed border-zinc-800 p-5 text-center text-xs text-zinc-500">Дедлайнов пока нет</div> : <div className="mt-4 space-y-2">{sorted.map(item => <div key={item.id} className="group rounded-xl border border-zinc-800 bg-zinc-950/40 p-3"><div className="flex items-start justify-between gap-2"><div className="min-w-0"><p className="truncate text-xs font-semibold text-zinc-200">{item.title}</p><p className="mt-1 text-[11px] text-zinc-500">{formatCountdownDate(item.target_date)} · {item.category || 'личное'}</p></div><button type="button" onClick={() => onDelete(item)} className="text-[10px] text-zinc-600 opacity-0 transition-opacity hover:text-rose-300 group-hover:opacity-100">Удалить</button></div><p className={`mt-2 text-[11px] font-semibold ${item.days_remaining < 0 ? 'text-rose-300' : item.days_remaining <= 7 ? 'text-amber-300' : 'text-emerald-300'}`}>{item.days_remaining < 0 ? `Просрочен на ${Math.abs(item.days_remaining)} дн.` : item.days_remaining === 0 ? 'Сегодня' : `Через ${item.days_remaining} дн.`}</p></div>)}</div>}</Card>;
}

function PeriodPicker({ anchorDate, pickerMonth, range, searchTerm, searchQuery, onMonthChange, onChooseDate, onSearchTermChange, onClose }: { anchorDate: Date; pickerMonth: Date; range: CalendarRange; searchTerm: string; searchQuery: { data?: CalendarEvent[]; isFetching: boolean }; onMonthChange: (date: Date) => void; onChooseDate: (date: Date) => void; onSearchTermChange: (value: string) => void; onClose: () => void }) {
  const days = getMonthDays(pickerMonth);
  return <div className="absolute left-0 top-[calc(100%+8px)] z-30 w-[min(340px,calc(100vw-32px))] rounded-2xl border border-zinc-700 bg-zinc-900 p-3 shadow-2xl">
    <div className="mb-3 flex items-center justify-between"><Button onClick={() => onMonthChange(shiftAnchor('month', pickerMonth, -1))} aria-label="Предыдущий месяц"><ChevronLeft className="h-4 w-4" /></Button><span className="text-xs font-semibold capitalize text-zinc-200">{pickerMonth.toLocaleDateString('ru-RU', { month: 'long', year: 'numeric' })}</span><Button onClick={() => onMonthChange(shiftAnchor('month', pickerMonth, 1))} aria-label="Следующий месяц"><ChevronRight className="h-4 w-4" /></Button></div>
    <div className="grid grid-cols-7 gap-1 text-center">{WEEKDAYS.map(day => <span key={day} className="py-1 text-[10px] font-semibold text-zinc-600">{day}</span>)}{days.map(day => { const key = formatLocalDate(day); const selected = range === 'month' ? day.getMonth() === anchorDate.getMonth() && day.getFullYear() === anchorDate.getFullYear() : key === formatLocalDate(anchorDate); const today = key === formatLocalDate(new Date()); return <button key={key} type="button" onClick={() => onChooseDate(day)} className={`h-8 rounded-lg text-xs transition-colors hover:bg-zinc-800 ${day.getMonth() !== pickerMonth.getMonth() ? 'text-zinc-700' : today ? 'bg-emerald-500/15 text-emerald-300' : selected ? 'bg-zinc-700 text-zinc-100' : 'text-zinc-400'}`}>{day.getDate()}</button>; })}</div>
    <div className="mt-3 border-t border-zinc-800 pt-3"><label className="relative block"><Search className="pointer-events-none absolute left-3 top-2.5 h-4 w-4 text-zinc-600" /><input value={searchTerm} onChange={event => onSearchTermChange(event.target.value)} className="input pl-9" placeholder="Найти событие…" /></label>{searchTerm.trim().length >= 2 && <div className="mt-2 max-h-36 space-y-1 overflow-y-auto">{searchQuery.isFetching ? <p className="px-2 py-2 text-xs text-zinc-500">Ищу…</p> : searchQuery.data?.length ? searchQuery.data.slice(0, 6).map(event => <button key={`${event.uid}-${event.start}`} type="button" onClick={() => { onChooseDate(parseEventDate(event.start)); onClose(); }} className="block w-full truncate rounded-lg px-2 py-2 text-left text-xs text-zinc-300 hover:bg-zinc-800"><span className="text-sky-300">{event.summary}</span><span className="ml-2 text-zinc-600">{getEventDateKey(event.start)}</span></button>) : <p className="px-2 py-2 text-xs text-zinc-500">Ничего не найдено</p>}</div>}</div>
    <button type="button" onClick={() => { onChooseDate(new Date()); onClose(); }} className="mt-3 flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-800 px-3 py-2 text-xs font-semibold text-zinc-400 hover:border-zinc-700 hover:text-zinc-200"><CalendarDays className="h-4 w-4" />Перейти к сегодня</button>
  </div>;
}

function SourcePicker({ sources, hiddenCalendars, onToggle, onClose }: { sources: CalendarSource[]; hiddenCalendars: string[]; onToggle: (calendarId: string) => void; onClose: () => void }) {
  return <div className="absolute left-0 top-[calc(100%+8px)] z-30 w-64 rounded-2xl border border-zinc-700 bg-zinc-900 p-3 shadow-2xl"><div className="mb-2 flex items-center justify-between"><span className="text-xs font-semibold text-zinc-300">Источники</span><button type="button" onClick={onClose} aria-label="Закрыть"><X className="h-4 w-4 text-zinc-500" /></button></div>{sources.map(source => { const hidden = hiddenCalendars.includes(source.calendar_id); return <label key={source.calendar_id} className="flex cursor-pointer items-center gap-2 rounded-lg px-2 py-2 text-xs text-zinc-300 hover:bg-zinc-800"><input type="checkbox" checked={!hidden} onChange={() => onToggle(source.calendar_id)} className="h-4 w-4 accent-emerald-500" /><span className="h-2.5 w-2.5 rounded-full" style={{ backgroundColor: sourceColor(source.calendar_name, source.calendar_color) }} />{source.calendar_name}<Check className={`ml-auto h-3.5 w-3.5 ${hidden ? 'invisible' : 'text-emerald-400'}`} /></label>; })}</div>;
}

function RangeButton({ active, children, onClick }: { active: boolean; children: string; onClick: () => void }) {
  return <button type="button" onClick={onClick} className={`rounded-lg px-3 py-2 text-xs font-semibold transition-colors ${active ? 'bg-emerald-500/15 text-emerald-300 shadow-sm' : 'text-zinc-500 hover:text-zinc-200'}`}>{children}</button>;
}

function Field({ label, children }: { label: string; children: ReactNode }) {
  return <label className="block text-xs font-semibold text-zinc-400"><span className="mb-1.5 block">{label}</span>{children}</label>;
}
