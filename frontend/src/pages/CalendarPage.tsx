import { useState, useEffect } from 'react';
import { 
  Calendar as CalendarIcon, 
  Clock, 
  Plus, 
  Edit2, 
  Trash2, 
  Loader2, 
  AlertCircle, 
  X, 
  FileText
} from 'lucide-react';
import { 
  fetchEvents, 
  createEvent, 
  modifyEvent, 
  deleteEvent 
} from '../api/calendar';
import type { CalendarEvent } from '../api/calendar';

interface EventFormState {
  uid?: string;
  title: string;
  date: string;
  startTime: string;
  endTime: string;
  description: string;
}

function getRangeDates(range: 'today' | 'week' | 'month'): { startStr: string; endStr: string } {
  const now = new Date();
  
  const formatLocalDate = (d: Date) => {
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  if (range === 'today') {
    const dateStr = formatLocalDate(now);
    return {
      startStr: `${dateStr}T00:00:00`,
      endStr: `${dateStr}T23:59:59`
    };
  } else if (range === 'week') {
    const currentDay = now.getDay();
    const distanceToMonday = currentDay === 0 ? 6 : currentDay - 1;
    const monday = new Date(now);
    monday.setDate(now.getDate() - distanceToMonday);
    
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    return {
      startStr: `${formatLocalDate(monday)}T00:00:00`,
      endStr: `${formatLocalDate(sunday)}T23:59:59`
    };
  } else {
    const year = now.getFullYear();
    const month = now.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    return {
      startStr: `${formatLocalDate(firstDay)}T00:00:00`,
      endStr: `${formatLocalDate(lastDay)}T23:59:59`
    };
  }
}

export default function CalendarPage() {
  const [range, setRange] = useState<'today' | 'week' | 'month'>('week');
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  
  // Modal states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formState, setFormState] = useState<EventFormState>({
    title: '',
    date: '',
    startTime: '',
    endTime: '',
    description: '',
  });
  const [submitting, setSubmitting] = useState<boolean>(false);

  // Load events
  const loadEvents = async () => {
    setLoading(true);
    setError(null);
    try {
      const { startStr, endStr } = getRangeDates(range);
      const data = await fetchEvents(startStr, endStr);
      
      // Sort chronologically by start date
      const sorted = [...data].sort((a, b) => {
        return new Date(a.start).getTime() - new Date(b.start).getTime();
      });
      
      setEvents(sorted);
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки календаря');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEvents();
  }, [range]);

  const handleDelete = async (uid: string) => {
    if (!window.confirm('Вы действительно хотите удалить это событие?')) {
      return;
    }
    
    try {
      await deleteEvent(uid);
      setEvents((prev) => prev.filter((ev) => ev.uid !== uid));
    } catch (err: any) {
      alert(`Ошибка при удалении: ${err.message}`);
    }
  };

  const handleOpenCreate = () => {
    const todayStr = new Date().toISOString().substring(0, 10);
    setFormState({
      title: '',
      date: todayStr,
      startTime: '12:00',
      endTime: '13:00',
      description: '',
    });
    setIsModalOpen(true);
  };

  const handleOpenEdit = (event: CalendarEvent) => {
    // Parse date and time from event.start and event.end
    // Format can be "2026-07-10 12:00:00" or similar
    const parseDateTime = (str: string) => {
      if (!str) return { date: '', time: '' };
      const parts = str.split(/[T ]/);
      const date = parts[0];
      const time = parts[1] ? parts[1].substring(0, 5) : '00:00';
      return { date, time };
    };

    const startInfo = parseDateTime(event.start);
    const endInfo = parseDateTime(event.end);

    setFormState({
      uid: event.uid,
      title: event.summary,
      date: startInfo.date || new Date().toISOString().substring(0, 10),
      startTime: startInfo.time || '12:00',
      endTime: endInfo.time || '13:00',
      description: event.description || '',
    });
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!formState.title.trim()) return;

    setSubmitting(true);
    try {
      // Build ISO 8601 strings
      const start_datetime = `${formState.date}T${formState.startTime}:00`;
      const end_datetime = `${formState.date}T${formState.endTime}:00`;

      if (formState.uid) {
        // Edit mode
        await modifyEvent(formState.uid, {
          title: formState.title,
          start_datetime,
          end_datetime,
          description: formState.description || undefined
        });
      } else {
        // Create mode
        await createEvent({
          title: formState.title,
          start_datetime,
          end_datetime,
          description: formState.description || undefined
        });
      }

      setIsModalOpen(false);
      loadEvents();
    } catch (err: any) {
      alert(`Ошибка сохранения: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const formatEventTime = (startStr: string, endStr: string) => {
    const parse = (str: string) => {
      // Parse ISO-like format
      const dateObj = new Date(str.replace(' ', 'T'));
      return isNaN(dateObj.getTime()) ? null : dateObj;
    };

    const startD = parse(startStr);
    const endD = parse(endStr);

    if (!startD) return 'Время не указано';

    const timeOptions: Intl.DateTimeFormatOptions = { hour: '2-digit', minute: '2-digit' };
    const dateOptions: Intl.DateTimeFormatOptions = { day: 'numeric', month: 'long' };

    const formattedDate = startD.toLocaleDateString('ru-RU', dateOptions);
    const startTime = startD.toLocaleTimeString('ru-RU', timeOptions);
    
    if (endD) {
      const endTime = endD.toLocaleTimeString('ru-RU', timeOptions);
      return `${formattedDate}, ${startTime} — ${endTime}`;
    }

    return `${formattedDate}, ${startTime}`;
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-indigo-500 shadow-[0_0_8px_#6366f1]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Расписание и Календарь
          </h1>
        </div>

        <div className="text-xs text-zinc-500 font-mono hidden md:block">
          Home Agent Calendar API
        </div>
      </header>

      {/* Main content body */}
      <main className="flex-1 overflow-y-auto w-full h-full flex flex-col">
        {/* Controls Bar */}
        <div className="flex flex-col sm:flex-row gap-4 justify-between items-center px-6 py-5 bg-zinc-950/40 border-b border-zinc-900 shrink-0">
          {/* Time range tab switcher */}
          <div className="flex bg-zinc-900 border border-zinc-800/80 rounded-xl p-1 w-full sm:w-auto">
            <button
              onClick={() => setRange('today')}
              className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                range === 'today'
                  ? 'bg-indigo-650 text-zinc-100 shadow-md shadow-indigo-900/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Сегодня
            </button>
            <button
              onClick={() => setRange('week')}
              className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                range === 'week'
                  ? 'bg-indigo-650 text-zinc-100 shadow-md shadow-indigo-900/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Эта неделя
            </button>
            <button
              onClick={() => setRange('month')}
              className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                range === 'month'
                  ? 'bg-indigo-650 text-zinc-100 shadow-md shadow-indigo-900/30'
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              Этот месяц
            </button>
          </div>

          {/* Action button */}
          <button
            onClick={handleOpenCreate}
            className="flex items-center justify-center gap-2 w-full sm:w-auto bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-lg shadow-indigo-950/20"
          >
            <Plus className="h-4 w-4" />
            Добавить событие
          </button>
        </div>

        {/* Display Content Area */}
        <div className="flex-1 w-full p-6">
          {loading ? (
            <div className="w-full h-64 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-indigo-500" />
              <span className="text-zinc-500 text-xs font-medium">Подключение к CalDAV...</span>
            </div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/20 text-red-200 text-xs px-5 py-4 rounded-xl flex items-center gap-3 max-w-xl mx-auto mt-6">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <div className="flex-1">
                <span className="font-bold">Ошибка:</span> {error}
              </div>
              <button 
                onClick={loadEvents}
                className="bg-red-950/40 hover:bg-red-900/40 text-red-300 font-semibold px-3 py-1.5 rounded-lg text-[10px] tracking-wide transition-all uppercase border border-red-500/20"
              >
                Повторить
              </button>
            </div>
          ) : events.length === 0 ? (
            <div className="w-full max-w-md mx-auto h-64 flex flex-col items-center justify-center gap-4 text-center border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/20 px-6 mt-6">
              <CalendarIcon className="h-10 w-10 text-zinc-650" />
              <div>
                <h3 className="text-sm font-semibold text-zinc-300">События отсутствуют</h3>
                <p className="text-zinc-500 text-xs mt-1">Нет запланированных встреч на выбранный период времени.</p>
              </div>
              <button 
                onClick={handleOpenCreate}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300 transition-colors"
              >
                Создать событие
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {events.map((event) => (
                <div 
                  key={event.uid}
                  className="bg-zinc-900/40 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all flex flex-col justify-between group shadow-md hover:shadow-lg"
                >
                  <div className="flex flex-col gap-3.5">
                    {/* Header */}
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex items-center gap-3.5 min-w-0">
                        <div className="p-2.5 rounded-xl bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 shrink-0">
                          <CalendarIcon className="h-4.5 w-4.5" />
                        </div>
                        <h2 className="text-sm font-semibold text-zinc-200 tracking-wide truncate pr-2">
                          {event.summary}
                        </h2>
                      </div>
                    </div>

                    {/* Time details */}
                    <div className="flex items-center gap-2 text-zinc-400">
                      <Clock className="h-3.5 w-3.5 text-zinc-500 shrink-0" />
                      <span className="text-[11px] font-medium leading-none">
                        {formatEventTime(event.start, event.end)}
                      </span>
                    </div>

                    {/* Description */}
                    {event.description && (
                      <div className="flex gap-2 text-zinc-500 mt-1">
                        <FileText className="h-3.5 w-3.5 text-zinc-650 shrink-0 mt-0.5" />
                        <p className="text-xs leading-relaxed font-sans line-clamp-3">
                          {event.description}
                        </p>
                      </div>
                    )}
                  </div>

                  {/* Actions footer */}
                  <div className="flex justify-end gap-2 border-t border-zinc-800/40 pt-4.5 mt-5">
                    <button
                      onClick={() => handleOpenEdit(event)}
                      className="p-2 rounded-xl text-zinc-450 hover:text-indigo-400 hover:bg-indigo-500/10 transition-all border border-transparent hover:border-indigo-500/20"
                      title="Редактировать"
                    >
                      <Edit2 className="h-4 w-4" />
                    </button>
                    <button
                      onClick={() => handleDelete(event.uid)}
                      className="p-2 rounded-xl text-zinc-450 hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20"
                      title="Удалить"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Create / Edit Form Modal */}
      {isModalOpen && (
        <div className="fixed inset-0 bg-black/65 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div 
            className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-md p-6 relative flex flex-col gap-5 text-zinc-100 shadow-[0_10px_35px_rgba(0,0,0,0.55)] max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setIsModalOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Modal Title */}
            <div>
              <h2 className="text-base font-bold text-zinc-200">
                {formState.uid ? 'Редактировать событие' : 'Создать новое событие'}
              </h2>
              <p className="text-zinc-500 text-[11px] mt-0.5">
                {formState.uid ? 'Измените параметры существующего события' : 'Заполните параметры для добавления события в календарь iCloud'}
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleFormSubmit} className="flex flex-col gap-4.5">
              {/* Event Title */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Название события *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Например: Встреча с DHL"
                  value={formState.title}
                  onChange={(e) => setFormState((prev) => ({ ...prev, title: e.target.value }))}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all"
                />
              </div>

              {/* Date */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Дата *
                </label>
                <input
                  type="date"
                  required
                  value={formState.date}
                  onChange={(e) => setFormState((prev) => ({ ...prev, date: e.target.value }))}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all font-sans"
                />
              </div>

              {/* Start and End Times */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                    Время начала
                  </label>
                  <input
                    type="time"
                    required
                    value={formState.startTime}
                    onChange={(e) => setFormState((prev) => ({ ...prev, startTime: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-850 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all"
                  />
                </div>
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                    Время окончания
                  </label>
                  <input
                    type="time"
                    required
                    value={formState.endTime}
                    onChange={(e) => setFormState((prev) => ({ ...prev, endTime: e.target.value }))}
                    className="w-full bg-zinc-950 border border-zinc-850 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all"
                  />
                </div>
              </div>

              {/* Description */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Описание
                </label>
                <textarea
                  placeholder="Добавьте детали события..."
                  rows={3}
                  value={formState.description}
                  onChange={(e) => setFormState((prev) => ({ ...prev, description: e.target.value }))}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-indigo-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none focus:ring-1 focus:ring-indigo-500/30 transition-all resize-none font-sans"
                />
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 justify-end border-t border-zinc-800/40 pt-4 mt-1.5">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-indigo-850 active:bg-indigo-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-md shadow-indigo-950/20"
                >
                  {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  {formState.uid ? 'Сохранить изменения' : 'Создать событие'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
