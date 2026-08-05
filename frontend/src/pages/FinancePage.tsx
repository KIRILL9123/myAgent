import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import { 
  Plus, 
  Loader2, 
  AlertCircle, 
  X,
  PlusCircle,
  MinusCircle,
  Repeat
} from 'lucide-react';
import {
  createTransaction,
  deleteTransaction,
  deleteRecurringTemplate
} from '../api/finance';
import { useFinanceData } from '../hooks/useFinanceData';
import type { FinanceRange } from '../types';
import { fetchSubscriptions } from '../api/subscriptions';
import type { Subscription } from '../api/subscriptions';
import FinanceSummaryCards from '../components/finance/FinanceSummaryCards';
import TransactionCard from '../components/finance/TransactionCard';
import RecurringTemplateCard from '../components/finance/RecurringTemplateCard';
import { Dialog, Button } from '../components/ui';

import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const FINANCE_CATEGORIES = [
  'Еда',
  'Транспорт/Бензин',
  'Авто (запчасти/ремонт)',
  'Гейминг/Хобби',
  'Подписки',
  'Разное',
  'Зарплата/Стипендия',
  'Фриланс/Разработка',
  'Продажа вещей'
];

export default function FinancePage() {
  const [range, setRange] = useState<FinanceRange>('month');
  const { transactions, summary, recurringTemplates, forecast, loading, error, reload: loadData } = useFinanceData(range);
  const subscriptionsQuery = useQuery({ queryKey: ['subscriptions'], queryFn: () => fetchSubscriptions(), staleTime: 5 * 60 * 1000 });
  const subscriptions = subscriptionsQuery.data ?? [];
  const proposedSubscriptions = subscriptions.filter(item => item.status === 'PROPOSED');
  const activeSubscriptions = subscriptions.filter(item => item.status === 'ACTIVE');

  // Form states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formType, setFormType] = useState<'income' | 'expense'>('expense');
  const [formAmount, setFormAmount] = useState<string>('');
  const [formCurrency, setFormCurrency] = useState<string>('EUR');
  const [formCategory, setFormCategory] = useState<string>(FINANCE_CATEGORIES[0]);
  const [formDescription, setFormDescription] = useState<string>('');
  const [formDate, setFormDate] = useState<string>('');
  const [formIsRecurring, setFormIsRecurring] = useState<boolean>(false);
  const [formFrequency, setFormFrequency] = useState<'weekly' | 'monthly' | 'yearly'>('monthly');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<{ kind: 'transaction' | 'template'; id: number; label: string } | null>(null);

  const handleDelete = (id: number) => setPendingRemoval({ kind: 'transaction', id, label: 'Удалить эту операцию?' });
  const handleDeleteTemplate = (id: number) => setPendingRemoval({ kind: 'template', id, label: 'Остановить этот повторяющийся платёж?' });
  const confirmRemoval = async () => {
    if (!pendingRemoval) return;
    try {
      if (pendingRemoval.kind === 'transaction') await deleteTransaction(pendingRemoval.id); else await deleteRecurringTemplate(pendingRemoval.id);
      setPendingRemoval(null);
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Не удалось удалить запись');
    }
  };

  const handleOpenCreate = () => {
    const todayStr = new Date().toISOString().substring(0, 10);
    setFormType('expense');
    setFormAmount('');
    setFormCurrency('EUR');
    setFormCategory('Еда');
    setFormDescription('');
    setFormDate(todayStr);
    setFormIsRecurring(false);
    setFormFrequency('monthly');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountNum = parseFloat(formAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setActionError('Сумма должна быть положительным числом');
      return;
    }

    setSubmitting(true);
    try {
      await createTransaction({
        type: formType,
        amount: amountNum,
        currency: formCurrency,
        category: formCategory,
        description: formDescription,
        date: formDate,
        is_recurring: formIsRecurring,
        frequency: formFrequency,
      });
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      setActionError(err instanceof Error ? err.message : 'Не удалось сохранить транзакцию');
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (val: number, currency = 'EUR') => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency, minimumFractionDigits: 2 }).format(val);
  };

  const formatDateString = (str: string) => {
    if (!str) return '';
    const dateObj = new Date(str);
    if (isNaN(dateObj.getTime())) return str;
    return dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Учет Финансов
          </h1>
        </div>

      </header>

      {/* Main Container */}
      <main className="flex-1 overflow-y-auto w-full h-full flex flex-col">
        {/* Controls and Summary Header */}
        <div className="flex flex-col gap-5 px-6 py-5 bg-zinc-950/40 border-b border-zinc-900 shrink-0">
          <div className="flex flex-col sm:flex-row gap-4 justify-between items-center w-full">
            {/* Range Tabs */}
            <div className="flex bg-zinc-900 border border-zinc-800/80 rounded-xl p-1 w-full sm:w-auto">
              <button
                onClick={() => setRange('today')}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  range === 'today'
                    ? 'bg-emerald-650 text-zinc-100 shadow-md shadow-emerald-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Сегодня
              </button>
              <button
                onClick={() => setRange('week')}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  range === 'week'
                    ? 'bg-emerald-650 text-zinc-100 shadow-md shadow-emerald-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Эта неделя
              </button>
              <button
                onClick={() => setRange('month')}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  range === 'month'
                    ? 'bg-emerald-650 text-zinc-100 shadow-md shadow-emerald-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Этот месяц
              </button>
            </div>

            {/* Action button */}
            <button
              onClick={handleOpenCreate}
              className="flex items-center justify-center gap-2 w-full sm:w-auto bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-lg shadow-emerald-950/20"
            >
              <Plus className="h-4 w-4" />
              Добавить транзакцию
            </button>
          </div>
          {actionError && <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-xs text-rose-200"><span>{actionError}</span><button onClick={() => setActionError(null)} className="text-rose-300 hover:text-rose-100">Скрыть</button></div>}

          {/* Finance summary indicators */}
          {summary && !loading && (
            <FinanceSummaryCards summary={summary} formatCurrency={formatCurrency} />
          )}
        </div>

        {/* Display Content Area */}
        <div className="flex-1 w-full p-6 flex flex-col gap-6">
          {loading ? (
            <div className="w-full h-64 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-emerald-500" />
              <span className="text-zinc-500 text-xs font-medium">Синхронизация бюджета...</span>
            </div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/20 text-red-200 text-xs px-5 py-4 rounded-xl flex items-center gap-3 max-w-xl mx-auto mt-6">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <div className="flex-1">
                <span className="font-bold">Ошибка:</span> {error}
              </div>
              <button 
                onClick={loadData}
                className="bg-red-950/40 hover:bg-red-900/40 text-red-300 font-semibold px-3 py-1.5 rounded-lg text-[10px] tracking-wide transition-all uppercase border border-red-500/25"
              >
                Повторить
              </button>
            </div>
          ) : (
            <>
              {/* Category charts section */}
              {summary && summary.expense_breakdown.length > 0 && (
                <div className="bg-zinc-900/20 border border-zinc-900 rounded-2xl p-5">
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-4">
                    Расходы по категориям ({range === 'today' ? 'сегодня' : range === 'week' ? 'неделя' : 'месяц'})
                  </h3>
                  <div className="w-full h-[220px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={summary.expense_breakdown} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis dataKey="category" stroke="#71717a" fontSize={10} tickLine={false} />
                        <YAxis stroke="#71717a" fontSize={10} tickLine={false} />
                        <Tooltip 
                          contentStyle={{ backgroundColor: '#18181b', borderColor: '#27272a', borderRadius: '12px' }} 
                          labelStyle={{ color: '#a1a1aa', fontWeight: 'bold', fontSize: '11px' }}
                          itemStyle={{ color: '#f43f5e', fontSize: '11px' }}
                        />
                        <Bar dataKey="amount" fill="#f43f5e" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Transactions grid */}
              <div>
                <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider mb-4">Журнал операций</h3>
                {transactions.length === 0 ? (
                  <div className="w-full max-w-md mx-auto h-32 flex flex-col items-center justify-center gap-2 border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/20 px-6">
                    <p className="text-zinc-500 text-xs">Нет операций за этот период.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {transactions.map((tx) => (
                      <TransactionCard
                        key={tx.id}
                        transaction={tx}
                        formatDate={formatDateString}
                        formatCurrency={formatCurrency}
                        onDelete={handleDelete}
                      />
                    ))}
                  </div>
                )}
              </div>

              {/* Recurring subscriptions panel */}
              <div className="border-t border-zinc-900 pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <Repeat className="h-4 w-4 text-emerald-500" />
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                    Активные повторяющиеся операции
                  </h3>
                </div>
                
                {recurringTemplates.length === 0 ? (
                  <div className="w-full h-24 flex items-center justify-center border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/15">
                    <p className="text-zinc-600 text-xs font-sans">Нет повторяющихся операций.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {recurringTemplates.map((template) => (
                      <RecurringTemplateCard
                        key={template.id}
                        template={template}
                        formatCurrency={formatCurrency}
                        onDelete={handleDeleteTemplate}
                      />
                    ))}
                  </div>
                )}
              </div>

              {forecast && (
                <section className="border-t border-zinc-900 pt-6">
                  <div className="flex items-center justify-between gap-3 mb-4">
                    <div>
                      <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Прогноз на 3 месяца</h3>
                      <p className="mt-1 text-[11px] text-zinc-600">Только активные повторяющиеся шаблоны, без конвертации валют.</p>
                    </div>
                    <span className="text-[11px] text-zinc-600">{formatDateString(forecast.start_date)} — {formatDateString(forecast.end_date)}</span>
                  </div>
                  {forecast.currencies.length === 0 ? (
                    <div className="rounded-xl border border-dashed border-zinc-800 px-4 py-5 text-xs text-zinc-600">Нет запланированных повторений.</div>
                  ) : (
                    <div className="grid gap-3 md:grid-cols-2">
                      {forecast.currencies.map((currency) => {
                        const totals = forecast.by_currency[currency];
                        return (
                          <div key={currency} className="rounded-xl border border-zinc-800 bg-zinc-950/25 p-4">
                            <div className="flex items-center justify-between gap-3">
                              <span className="text-xs font-semibold text-zinc-200">{currency}</span>
                              <span className={`text-xs font-mono font-semibold ${totals.net_balance >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                                {formatCurrency(totals.net_balance, currency)}
                              </span>
                            </div>
                            <div className="mt-3 grid grid-cols-3 gap-2 text-[10px]">
                              <div><span className="block text-zinc-600">Доходы</span><span className="text-emerald-300">{formatCurrency(totals.total_income, currency)}</span></div>
                              <div><span className="block text-zinc-600">Расходы</span><span className="text-rose-300">{formatCurrency(totals.total_expense, currency)}</span></div>
                              <div><span className="block text-zinc-600">Повторения</span><span className="text-zinc-300">{totals.occurrences}</span></div>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {forecast.occurrences.length > 0 && (
                    <div className="mt-3 divide-y divide-zinc-900 rounded-xl border border-zinc-900 bg-zinc-950/15">
                      {forecast.occurrences.slice(0, 6).map((occurrence) => (
                        <div key={`${occurrence.template_id}-${occurrence.date}`} className="flex items-center justify-between gap-3 px-4 py-3 text-xs">
                          <div className="min-w-0"><p className="truncate text-zinc-300">{occurrence.description || occurrence.category}</p><p className="mt-0.5 text-[10px] text-zinc-600">{formatDateString(occurrence.date)} · {occurrence.frequency}</p></div>
                          <span className={`shrink-0 font-mono ${occurrence.type === 'income' ? 'text-emerald-300' : 'text-rose-300'}`}>{occurrence.type === 'income' ? '+' : '-'}{formatCurrency(occurrence.amount, occurrence.currency)}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </section>
              )}

              <SubscriptionsSnapshot subscriptions={subscriptions} proposed={proposedSubscriptions} active={activeSubscriptions} loading={subscriptionsQuery.isLoading} error={subscriptionsQuery.error} formatDate={formatDateString} />
            </>
          )}
        </div>
      </main>

      {/* Add Transaction Modal */}
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
              title="Закрыть"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Modal Title */}
            <div>
              <h2 className="text-base font-bold text-zinc-200">
                Новая транзакция
              </h2>
              <p className="text-zinc-500 text-[11px] mt-0.5">
                Заполните форму для добавления операции в журнал финансов
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleFormSubmit} className="flex flex-col gap-4.5">
              {/* Type Switcher */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Тип транзакции *
                </label>
                <div className="grid grid-cols-2 bg-zinc-950 p-1 border border-zinc-850 rounded-xl">
                  <button
                    type="button"
                    onClick={() => setFormType('expense')}
                    className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                      formType === 'expense'
                        ? 'bg-rose-500/10 text-rose-400 border border-rose-500/20'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <MinusCircle className="h-4 w-4" />
                    Расход
                  </button>
                  <button
                    type="button"
                    onClick={() => setFormType('income')}
                    className={`py-2 rounded-lg text-xs font-bold transition-all flex items-center justify-center gap-1.5 ${
                      formType === 'income'
                        ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                        : 'text-zinc-400 hover:text-zinc-200'
                    }`}
                  >
                    <PlusCircle className="h-4 w-4" />
                    Доход
                  </button>
                </div>
              </div>

              {/* Amount */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Сумма (€) *
                </label>
                <input
                  type="number"
                  required
                  step="any"
                  placeholder="0"
                  value={formAmount}
                  onChange={(e) => setFormAmount(e.target.value)}
                  className="w-full bg-zinc-955 border border-zinc-850 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all font-mono"
                />
              </div>

              {/* Currency */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Валюта *
                </label>
                <select
                  value={formCurrency}
                  onChange={(e) => setFormCurrency(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans cursor-pointer"
                >
                  {['EUR', 'USD', 'GBP', 'UAH'].map((currency) => (
                    <option key={currency} value={currency}>{currency}</option>
                  ))}
                </select>
              </div>

              {/* Category */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-550 uppercase tracking-widest mb-1.5">
                  Категория *
                </label>
                <select
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-emerald-500 rounded-xl px-4.5 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans cursor-pointer"
                >
                  {FINANCE_CATEGORIES.map((cat) => (
                    <option key={cat} value={cat}>
                      {cat}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Дата операции *
                </label>
                <input
                  type="date"
                  required
                  value={formDate}
                  onChange={(e) => setFormDate(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans"
                />
              </div>

              {/* Description */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Описание
                </label>
                <textarea
                  placeholder="Дополнительные детали..."
                  rows={2}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all resize-none font-sans"
                />
              </div>

              {/* Recurring Switcher */}
              <div className="flex items-center gap-3 bg-zinc-950/40 p-3.5 border border-zinc-850 rounded-xl mt-1.5">
                <input
                  type="checkbox"
                  id="formIsRecurring"
                  checked={formIsRecurring}
                  onChange={(e) => setFormIsRecurring(e.target.checked)}
                  className="h-4 w-4 bg-zinc-950 border-zinc-850 focus:ring-emerald-500 text-emerald-600 rounded cursor-pointer"
                />
                <div className="flex flex-col gap-0.5 cursor-pointer select-none min-w-0" onClick={() => setFormIsRecurring(!formIsRecurring)}>
                  <label htmlFor="formIsRecurring" className="text-xs font-semibold text-zinc-250 flex items-center gap-1.5 cursor-pointer">
                    <Repeat className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                    Повторять операцию
                  </label>
                  <span className="text-[10px] text-zinc-550 leading-relaxed font-sans">
                    Создаст шаблон операции с выбранной частотой.
                  </span>
                </div>
              </div>

              {formIsRecurring && (
                <div>
                  <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                    Частота повторения
                  </label>
                  <select
                    value={formFrequency}
                    onChange={(e) => setFormFrequency(e.target.value as 'weekly' | 'monthly' | 'yearly')}
                    className="w-full bg-zinc-950 border border-zinc-850 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans cursor-pointer"
                  >
                    <option value="weekly">Каждую неделю</option>
                    <option value="monthly">Каждый месяц</option>
                    <option value="yearly">Каждый год</option>
                  </select>
                </div>
              )}

              {/* Form Actions */}
              <div className="flex gap-3 justify-end border-t border-zinc-800/40 pt-4 mt-1.5">
                <button
                  type="button"
                  onClick={() => setIsModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-450 hover:text-zinc-250 hover:bg-zinc-850 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-850 active:bg-emerald-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-md shadow-emerald-955/20"
                >
                  {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  Добавить транзакцию
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {pendingRemoval && <Dialog title={pendingRemoval.label} description={pendingRemoval.kind === 'template' ? 'Новые операции по этому шаблону больше не будут создаваться.' : 'Операция будет удалена из журнала финансов.'} onClose={() => setPendingRemoval(null)}><div className="flex justify-end gap-2"><Button onClick={() => setPendingRemoval(null)}>Отмена</Button><Button tone="danger" onClick={confirmRemoval}>Подтвердить</Button></div></Dialog>}
    </div>
  );
}

function SubscriptionsSnapshot({ subscriptions, proposed, active, loading, error, formatDate }: { subscriptions: Subscription[]; proposed: Subscription[]; active: Subscription[]; loading: boolean; error: unknown; formatDate: (value: string) => string }) {
  const visible = [...proposed, ...active].slice(0, 4);
  return <section className="border-t border-zinc-900 pt-6"><div className="flex flex-wrap items-center justify-between gap-3"><div><h2 className="text-sm font-semibold text-zinc-200">Подписки</h2><p className="mt-1 text-xs text-zinc-500">Регулярные платежи теперь рядом с финансами</p></div><Link to="/subscriptions" className="text-xs font-semibold text-emerald-300 hover:text-emerald-200">Открыть управление →</Link></div><div className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3"><div className="rounded-xl border border-zinc-800 bg-zinc-950/30 p-3"><p className="text-[10px] uppercase tracking-wider text-zinc-600">Всего</p><p className="mt-2 text-xl font-bold text-zinc-200">{subscriptions.length}</p></div><div className="rounded-xl border border-amber-500/15 bg-amber-500/5 p-3"><p className="text-[10px] uppercase tracking-wider text-zinc-600">На проверке</p><p className="mt-2 text-xl font-bold text-amber-300">{proposed.length}</p></div><div className="rounded-xl border border-emerald-500/15 bg-emerald-500/5 p-3"><p className="text-[10px] uppercase tracking-wider text-zinc-600">Активные</p><p className="mt-2 text-xl font-bold text-emerald-300">{active.length}</p></div></div>{loading ? <div className="mt-4 flex items-center gap-2 text-xs text-zinc-500"><Loader2 className="h-4 w-4 animate-spin" />Загружаю подписки…</div> : error ? <p className="mt-4 text-xs text-zinc-600">Подписки временно недоступны</p> : visible.length === 0 ? <p className="mt-4 rounded-xl border border-dashed border-zinc-800 p-4 text-xs text-zinc-600">Подписок пока нет</p> : <div className="mt-4 grid gap-2 md:grid-cols-2">{visible.map(item => { const deadline = item.next_charge_at || item.trial_ends_at; const status = item.status === 'PROPOSED' ? 'На проверке' : 'Активна'; return <div key={item.id} className="rounded-xl border border-zinc-800 bg-zinc-950/30 p-3"><div className="flex items-start justify-between gap-2"><div className="min-w-0"><p className="truncate text-xs font-semibold text-zinc-200">{item.name}</p><p className="mt-1 truncate text-[11px] text-zinc-500">{item.provider || 'Вручную'}</p></div><span className={`shrink-0 rounded-md px-2 py-1 text-[10px] font-semibold ${item.status === 'PROPOSED' ? 'bg-amber-500/10 text-amber-300' : 'bg-emerald-500/10 text-emerald-300'}`}>{status}</span></div>{deadline && <p className="mt-3 text-[11px] text-zinc-500">Ближайшая дата: {formatDate(deadline)}</p>}</div>; })}</div>}</section>;
}
