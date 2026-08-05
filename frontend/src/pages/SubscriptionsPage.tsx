import { useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import {
  AlertCircle, Bell, Check, CreditCard, Link as LinkIcon, Loader2, Mail,
  Plus, RefreshCw, Search, ShieldCheck, X,
} from 'lucide-react';
import {
  approveSubscription, cancelSubscription, createSubscription, fetchSubscriptions,
  scanEmailForSubscriptions,
} from '../api/subscriptions';
import type { Subscription, SubscriptionCreateInput, SubscriptionStatus } from '../api/subscriptions';

const STATUS_LABELS: Record<SubscriptionStatus, string> = {
  PROPOSED: 'Нужно проверить', ACTIVE: 'Отслеживается', CANCELLED: 'Отменённые', EXPIRED: 'Завершённые',
};

function formatDate(value: string | null): string {
  if (!value) return 'Дата не указана';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' });
}

function statusClass(status: SubscriptionStatus): string {
  if (status === 'PROPOSED') return 'text-amber-300 bg-amber-500/10 border-amber-500/20';
  if (status === 'ACTIVE') return 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20';
  return 'text-zinc-400 bg-zinc-800/60 border-zinc-700';
}

function price(item: Subscription): string {
  if (item.amount === null || item.amount === undefined) return 'Сумма не указана';
  return `${item.amount.toLocaleString('ru-RU')} ${item.currency || ''}`.trim();
}

function safeCancellationUrl(value: string | null): string | null {
  if (!value) return null;
  try {
    const parsed = new URL(value);
    return parsed.protocol === 'http:' || parsed.protocol === 'https:' ? value : null;
  } catch {
    return null;
  }
}

export default function SubscriptionsPage() {
  const [subscriptions, setSubscriptions] = useState<Subscription[]>([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [account, setAccount] = useState('gmail');
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<SubscriptionCreateInput>({ name: '', subscription_type: 'TRIAL', currency: 'EUR' });

  const load = async () => {
    setLoading(true); setError(null);
    try { setSubscriptions(await fetchSubscriptions()); }
    catch (err: any) { setError(err.message || 'Не удалось загрузить подписки'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const proposed = useMemo(() => subscriptions.filter(item => item.status === 'PROPOSED'), [subscriptions]);
  const active = useMemo(() => subscriptions.filter(item => item.status === 'ACTIVE'), [subscriptions]);
  const history = useMemo(() => subscriptions.filter(item => ['CANCELLED', 'EXPIRED'].includes(item.status)), [subscriptions]);

  const scan = async () => {
    setBusy(true); setError(null); setNotice(null);
    try {
      const result = await scanEmailForSubscriptions(account);
      await load();
      setNotice(`Проверено писем: ${result.scanned}. Новых предложений: ${result.proposals.length}.${result.errors.length ? ` Ошибок: ${result.errors.length}.` : ''}`);
    } catch (err: any) { setError(err.message || 'Не удалось проверить почту'); }
    finally { setBusy(false); }
  };

  const runAction = async (id: string, action: 'approve' | 'cancel') => {
    setBusyId(id); setError(null);
    try {
      if (action === 'approve') {
        const result = await approveSubscription(id);
        if (result.finance_link?.status === 'pending_approval') {
          setNotice('Подписка активирована. Отдельное подтверждение шаблона расходов появилось в Центре подтверждений.');
        } else if (result.finance_link?.status === 'not_eligible') {
          setNotice(`Подписка активирована без Finance-шаблона: ${result.finance_link.reason}`);
        }
      } else await cancelSubscription(id);
      await load();
    } catch (err: any) { setError(err.message || 'Не удалось изменить подписку'); }
    finally { setBusyId(null); }
  };

  const submitManual = async (event: FormEvent) => {
    event.preventDefault();
    if (!form.name?.trim()) return;
    setBusy(true); setError(null);
    try {
      await createSubscription({
        ...form,
        amount: form.amount === undefined ? undefined : Number(form.amount),
      });
      setForm({ name: '', subscription_type: 'TRIAL', currency: 'EUR' });
      setShowForm(false);
      await load();
    } catch (err: any) { setError(err.message || 'Не удалось добавить подписку'); }
    finally { setBusy(false); }
  };

  const renderCard = (item: Subscription) => {
    const deadline = item.next_charge_at || item.trial_ends_at;
    const cancellationUrl = safeCancellationUrl(item.cancellation_url);
    return (
      <article key={item.id} className="flex flex-col gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 shadow-lg">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 className="truncate text-sm font-semibold text-zinc-100">{item.name}</h2>
            {item.provider && <p className="mt-1 text-xs text-zinc-500">{item.provider}</p>}
          </div>
          <span className={`shrink-0 rounded-lg border px-2 py-1 text-[10px] font-bold ${statusClass(item.status)}`}>{STATUS_LABELS[item.status]}</span>
        </div>
        <div className="grid grid-cols-1 gap-3 text-[11px] text-zinc-400 sm:grid-cols-2">
          <div className="flex items-center gap-2"><CreditCard className="h-3.5 w-3.5 text-purple-400" />{price(item)}{item.billing_cycle ? ` · ${item.billing_cycle}` : ''}</div>
          <div className="flex items-center gap-2"><Bell className="h-3.5 w-3.5 text-amber-400" />Напоминание: {formatDate(item.reminder_at)}</div>
          <div className="flex items-start gap-2"><Search className="mt-0.5 h-3.5 w-3.5 text-blue-400" /><span>{item.next_charge_at ? 'Следующее списание' : 'Trial заканчивается'}: {formatDate(deadline)}</span></div>
          <div className="flex items-center gap-2"><Mail className="h-3.5 w-3.5 text-zinc-500" />Источник: {item.source_type === 'EMAIL' ? 'почта' : 'вручную'} · {Math.round(item.confidence * 100)}%</div>
        </div>
        {(cancellationUrl || item.cancellation_instructions) && (
          <div className="flex items-start gap-2 rounded-xl border border-blue-500/10 bg-blue-500/5 p-3 text-xs text-blue-200">
            <LinkIcon className="mt-0.5 h-3.5 w-3.5 shrink-0" />
            {cancellationUrl ? <a href={cancellationUrl} target="_blank" rel="noreferrer" className="truncate underline underline-offset-2">Открыть страницу отмены</a> : <span>{item.cancellation_instructions}</span>}
          </div>
        )}
        <div className="flex gap-2 border-t border-zinc-800 pt-3">
          {item.status === 'PROPOSED' && <button onClick={() => runAction(item.id, 'approve')} disabled={busyId === item.id} className="flex items-center gap-1.5 rounded-lg bg-emerald-600/80 px-3 py-2 text-[11px] font-semibold hover:bg-emerald-500"><ShieldCheck className="h-3.5 w-3.5" />Подтвердить</button>}
          {(item.status === 'PROPOSED' || item.status === 'ACTIVE') && <button onClick={() => runAction(item.id, 'cancel')} disabled={busyId === item.id} className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-[11px] font-semibold text-zinc-400 hover:border-red-500/50 hover:text-red-300"><X className="h-3.5 w-3.5" />Не отслеживать</button>}
          {busyId === item.id && <Loader2 className="h-4 w-4 animate-spin self-center text-zinc-500" />}
        </div>
      </article>
    );
  };

  const renderSection = (title: string, items: Subscription[], color: string, empty: string) => (
    <section><h2 className={`mb-3 text-xs font-bold uppercase tracking-widest ${color}`}>{title} · {items.length}</h2>{items.length ? <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">{items.map(renderCard)}</div> : <p className="rounded-xl border border-dashed border-zinc-800 p-6 text-sm text-zinc-600">{empty}</p>}</section>
  );

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex shrink-0 flex-col gap-4 border-b border-zinc-900 px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6 sm:py-4">
        <div className="flex min-w-0 items-center gap-3"><CreditCard className="h-5 w-5 shrink-0 text-purple-400" /><div className="min-w-0"><h1 className="truncate text-lg font-bold sm:text-xl">Подписки</h1><p className="mt-1 truncate text-xs text-zinc-500">Trial-периоды, списания и напоминания об отмене</p></div></div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={account} onChange={event => setAccount(event.target.value)} className="rounded-lg border border-zinc-800 bg-zinc-900 px-2.5 py-2 text-xs text-zinc-300"><option value="gmail">Gmail</option><option value="ukrnet">Ukr.net</option></select>
          <button onClick={scan} disabled={busy} className="flex items-center gap-1.5 rounded-lg bg-blue-600 px-3 py-2 text-xs font-semibold hover:bg-blue-500 disabled:opacity-50"><Search className="h-3.5 w-3.5" />Сканировать почту</button>
          <button onClick={() => setShowForm(value => !value)} className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-xs font-semibold text-zinc-300 hover:border-zinc-500"><Plus className="h-3.5 w-3.5" />Добавить</button>
          <button onClick={load} className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200"><RefreshCw className="h-4 w-4" /></button>
        </div>
      </header>
      <main className="flex-1 space-y-6 overflow-y-auto p-4 sm:space-y-8 sm:p-6">
        {error && <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-200"><AlertCircle className="h-4 w-4" />{error}</div>}
        {notice && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 p-4 text-xs text-emerald-200">{notice}</div>}
        {showForm && <form onSubmit={submitManual} className="grid grid-cols-1 gap-3 rounded-2xl border border-purple-500/20 bg-purple-500/5 p-4 sm:grid-cols-2 lg:grid-cols-4">
          <input required placeholder="Название подписки" value={form.name || ''} onChange={event => setForm({ ...form, name: event.target.value })} className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs outline-none focus:border-purple-500" />
          <select value={form.subscription_type} onChange={event => setForm({ ...form, subscription_type: event.target.value as SubscriptionCreateInput['subscription_type'] })} className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs"><option value="TRIAL">Trial</option><option value="PAID">Платная</option><option value="UNKNOWN">Неизвестно</option></select>
          <input type="number" min="0" step="0.01" placeholder="Сумма" value={form.amount ?? ''} onChange={event => setForm({ ...form, amount: event.target.value ? Number(event.target.value) : undefined })} className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs outline-none focus:border-purple-500" />
          <input placeholder="Валюта" value={form.currency || ''} onChange={event => setForm({ ...form, currency: event.target.value })} className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs outline-none focus:border-purple-500" />
          <label className="text-[10px] text-zinc-500">Trial заканчивается<input type="datetime-local" onChange={event => setForm({ ...form, trial_ends_at: event.target.value ? new Date(event.target.value).toISOString() : undefined })} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300" /></label>
          <label className="text-[10px] text-zinc-500">Следующее списание<input type="datetime-local" onChange={event => setForm({ ...form, next_charge_at: event.target.value ? new Date(event.target.value).toISOString() : undefined })} className="mt-1 w-full rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300" /></label>
          <input placeholder="Ссылка отмены" value={form.cancellation_url || ''} onChange={event => setForm({ ...form, cancellation_url: event.target.value })} className="rounded-lg border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs outline-none focus:border-purple-500" />
          <button type="submit" disabled={busy} className="flex items-center justify-center gap-1.5 rounded-lg bg-purple-600 px-3 py-2 text-xs font-semibold hover:bg-purple-500 disabled:opacity-50"><Check className="h-3.5 w-3.5" />Сохранить</button>
        </form>}
        {loading ? <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-purple-400" /></div> : <>{renderSection('Новые предложения из почты', proposed, 'text-amber-300', 'Предложений нет. Можно запустить сканирование почты.')}{renderSection('Активные подписки', active, 'text-emerald-300', 'Пока нет подписок под наблюдением.')}{history.length > 0 && renderSection('История', history, 'text-zinc-500', '')}</>}
      </main>
    </div>
  );
}
