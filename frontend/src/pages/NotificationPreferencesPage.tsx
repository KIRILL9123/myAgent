import { useEffect, useState } from 'react';
import type { FormEvent } from 'react';
import { Bell, Check, ChevronLeft, Clock3, Save, ShieldCheck } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { fetchNotificationPreferences, updateNotificationPreferences } from '../api/notifications';
import type { NotificationPreferences, NotificationPriority } from '../api/notifications';
import { Button, Card, ErrorState, LoadingState, PageHeader } from '../components/ui';

type PreferencesForm = Omit<NotificationPreferences, 'updated_at'>;

const PRIORITY_OPTIONS: Array<{ value: NotificationPriority; label: string; description: string }> = [
  { value: 'critical', label: 'Только срочные', description: 'Только критические сигналы.' },
  { value: 'high', label: 'Важные и срочные', description: 'Критические и важные сигналы.' },
  { value: 'medium', label: 'Обычный', description: 'Рекомендуемый уровень.' },
  { value: 'low', label: 'Все сигналы', description: 'Включая плановые.' },
];

const TIMEZONE_OPTIONS = ['Europe/Berlin', 'Europe/Kyiv', 'Europe/Warsaw', 'Europe/London', 'UTC', 'America/New_York'];

function toForm(value: NotificationPreferences): PreferencesForm {
  const { updated_at: _updatedAt, ...form } = value;
  return form;
}

function fieldClass(): string {
  return 'mt-1 w-full rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2.5 text-sm text-zinc-200 outline-none transition-colors focus:border-purple-500/60 focus:ring-2 focus:ring-purple-500/10';
}

export default function NotificationPreferencesPage() {
  const queryClient = useQueryClient();
  const query = useQuery({ queryKey: ['notification-preferences'], queryFn: fetchNotificationPreferences, staleTime: 60_000 });
  const [form, setForm] = useState<PreferencesForm | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    if (query.data) setForm(toForm(query.data));
  }, [query.data]);

  const mutation = useMutation({
    mutationFn: updateNotificationPreferences,
    onSuccess: (data) => {
      setForm(toForm(data));
      setNotice('Настройки уведомлений сохранены.');
      queryClient.setQueryData(['notification-preferences'], data);
    },
  });

  const update = <K extends keyof PreferencesForm>(key: K, value: PreferencesForm[K]) => {
    setNotice(null);
    setForm(current => current ? { ...current, [key]: value } : current);
  };

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (form) mutation.mutate(form);
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <PageHeader
        icon={<Bell className="h-5 w-5 text-purple-300" />}
        title="Настройки уведомлений"
        description="Управляйте тем, когда и какие сигналы доставлять"
        action={<Link to="/notifications" className="inline-flex min-h-10 items-center gap-1.5 rounded-xl border border-zinc-700 bg-zinc-900 px-3.5 py-2 text-xs font-semibold text-zinc-300 transition-colors hover:border-zinc-600 hover:text-zinc-100"><ChevronLeft className="h-4 w-4" />К уведомлениям</Link>}
      />
      <main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
        {query.isError && <ErrorState message={query.error instanceof Error ? query.error.message : 'Не удалось загрузить настройки'} onRetry={() => query.refetch()} />}
        {mutation.isError && <ErrorState message={mutation.error instanceof Error ? mutation.error.message : 'Не удалось сохранить настройки'} />}
        {notice && <div className="flex items-center gap-2 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-xs text-emerald-200"><Check className="h-4 w-4" />{notice}</div>}
        {query.isLoading || !form ? <LoadingState label="Загружаю настройки…" /> : (
          <form onSubmit={submit} className="mx-auto max-w-3xl space-y-5">
            <Card className="p-5 sm:p-6">
              <div className="flex items-start justify-between gap-4">
                <div><h2 className="text-sm font-semibold">Доставка уведомлений</h2><p className="mt-1 text-xs leading-relaxed text-zinc-500">Настройки применяются к Telegram-доставке Action Center. Сам экран уведомлений всегда остаётся доступен.</p></div>
                <label className="inline-flex shrink-0 cursor-pointer items-center gap-2 text-xs text-zinc-400"><input type="checkbox" checked={form.enabled} onChange={event => update('enabled', event.target.checked)} className="h-4 w-4 accent-purple-500" />Включена</label>
              </div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <label className="text-xs text-zinc-400">Часовой пояс
                  <input list="notification-timezones" value={form.timezone} onChange={event => update('timezone', event.target.value)} className={fieldClass()} placeholder="Europe/Berlin" />
                  <datalist id="notification-timezones">{TIMEZONE_OPTIONS.map(value => <option key={value} value={value} />)}</datalist>
                </label>
                <label className="text-xs text-zinc-400">Минимальный приоритет
                  <select value={form.min_priority} onChange={event => update('min_priority', event.target.value as NotificationPriority)} className={fieldClass()}>{PRIORITY_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
                  <span className="mt-1 block text-[11px] text-zinc-600">{PRIORITY_OPTIONS.find(option => option.value === form.min_priority)?.description}</span>
                </label>
              </div>
            </Card>

            <Card className="p-5 sm:p-6">
              <div className="flex items-start gap-3"><Clock3 className="mt-0.5 h-5 w-5 text-amber-300" /><div><h2 className="text-sm font-semibold">Тихие часы</h2><p className="mt-1 text-xs leading-relaxed text-zinc-500">Некритичные уведомления не отправляются в этот период. Срочные сигналы проходят всегда.</p></div></div>
              <div className="mt-5 grid gap-4 sm:grid-cols-2">
                <label className="text-xs text-zinc-400">Начало<input type="time" value={form.quiet_hours_start} onChange={event => update('quiet_hours_start', event.target.value)} className={fieldClass()} /></label>
                <label className="text-xs text-zinc-400">Окончание<input type="time" value={form.quiet_hours_end} onChange={event => update('quiet_hours_end', event.target.value)} className={fieldClass()} /></label>
              </div>
            </Card>

            <Card className="p-5 sm:p-6">
              <div className="flex items-start gap-3"><ShieldCheck className="mt-0.5 h-5 w-5 text-cyan-300" /><div><h2 className="text-sm font-semibold">Лимиты и объединение</h2><p className="mt-1 text-xs leading-relaxed text-zinc-500">Защищают от лишних сообщений, когда одновременно появляется много сигналов.</p></div></div>
              <div className="mt-5 grid gap-4 sm:grid-cols-3">
                <label className="text-xs text-zinc-400">Максимум сообщений<input type="number" min="1" max="50" value={form.max_messages_per_window} onChange={event => update('max_messages_per_window', Number(event.target.value))} className={fieldClass()} /></label>
                <label className="text-xs text-zinc-400">Окно лимита, минут<input type="number" min="5" max="1440" value={form.window_minutes} onChange={event => update('window_minutes', Number(event.target.value))} className={fieldClass()} /></label>
                <label className="text-xs text-zinc-400">Объединять в течение, минут<input type="number" min="1" max="1440" value={form.coalesce_window_minutes} onChange={event => update('coalesce_window_minutes', Number(event.target.value))} className={fieldClass()} /></label>
              </div>
            </Card>

            <div className="flex flex-wrap items-center justify-between gap-3"><p className="text-[11px] text-zinc-600">Критические уведомления не блокируются тихими часами и лимитом.</p><Button type="submit" tone="primary" loading={mutation.isPending}><Save className="h-4 w-4" />Сохранить настройки</Button></div>
          </form>
        )}
      </main>
    </div>
  );
}
