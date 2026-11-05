import FullCalendar from '@fullcalendar/react';
import dayGridPlugin from '@fullcalendar/daygrid';
import interactionPlugin from '@fullcalendar/interaction';
import timeGridPlugin from '@fullcalendar/timegrid';
import ruLocale from '@fullcalendar/core/locales/ru';
import type { CalendarEvent } from '../api/calendar';

type CalendarRange = 'today' | 'week' | 'month';

interface CalendarViewProps {
  range: CalendarRange;
  anchorDate: Date;
  events: CalendarEvent[];
  onEdit: (event: CalendarEvent) => void;
  onCreate: (date: Date) => void;
}

function normalizeDate(value: string) {
  return value.replace(' ', 'T');
}

function sourceColor(event: CalendarEvent) {
  if (event.calendar_color && /^#[0-9a-f]{6}$/i.test(event.calendar_color)) return event.calendar_color;
  const palette = ['#38bdf8', '#34d399', '#fbbf24', '#c084fc', '#fb7185', '#2dd4bf'];
  const hash = [...(event.calendar_name || 'Mira')].reduce((total, character) => total + character.charCodeAt(0), 0);
  return palette[hash % palette.length];
}

function viewName(range: CalendarRange) {
  if (range === 'today') return 'timeGridDay';
  if (range === 'month') return 'dayGridMonth';
  return 'timeGridWeek';
}

export default function CalendarView({ range, anchorDate, events, onEdit, onCreate }: CalendarViewProps) {
  const view = viewName(range);
  const calendarEvents = events.map(event => ({
    id: `${event.uid}-${event.start}`,
    title: event.summary,
    start: normalizeDate(event.start),
    end: normalizeDate(event.end),
    allDay: Boolean(event.all_day),
    backgroundColor: `${sourceColor(event)}2b`,
    borderColor: sourceColor(event),
    textColor: '#e5e7eb',
    classNames: event.conflicts?.length ? ['mira-calendar-event-conflict'] : [],
    extendedProps: { sourceEvent: event },
  }));

  return (
    <div className="mira-calendar-shell">
      <FullCalendar
        key={`${view}-${anchorDate.toISOString()}`}
        plugins={[dayGridPlugin, timeGridPlugin, interactionPlugin]}
        locales={[ruLocale]}
        locale="ru"
        initialView={view}
        initialDate={anchorDate}
        headerToolbar={false}
        height="auto"
        expandRows={range !== 'month'}
        nowIndicator={range !== 'month'}
        navLinks={false}
        selectable={false}
        editable={false}
        dayMaxEvents={range === 'month' ? 4 : false}
        slotMinTime="06:00:00"
        slotMaxTime="24:00:00"
        scrollTime="08:00:00"
        allDayText="Весь день"
        noEventsText="Событий нет"
        eventDisplay="block"
        displayEventTime
        eventTimeFormat={{ hour: '2-digit', minute: '2-digit', hour12: false }}
        dayHeaderFormat={{ weekday: 'short', day: 'numeric', month: range === 'month' ? undefined : 'short' }}
        events={calendarEvents}
        dateClick={info => onCreate(info.date)}
        eventClick={info => onEdit(info.event.extendedProps.sourceEvent as CalendarEvent)}
        eventDidMount={info => {
          const event = info.event.extendedProps.sourceEvent as CalendarEvent;
          info.el.setAttribute('aria-label', `Открыть событие: ${event.summary}`);
          info.el.title = event.conflicts?.length ? `${event.summary} · Есть конфликт` : event.summary;
        }}
      />
    </div>
  );
}
