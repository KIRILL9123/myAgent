import { useEffect, useMemo, useState, type FormEvent } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Loader2, AlertCircle, X, PlusCircle, MinusCircle, Repeat, Database, Search } from 'lucide-react';
import { createTransaction, deleteTransaction, deleteRecurringTemplate, updateTransaction } from '../api/finance';
import { useFinanceData } from '../hooks/useFinanceData';
import type { FinanceRange, Transaction, TransactionCreateInput, TransactionUpdateInput } from '../types';
import FinanceSummaryCards from '../components/finance/FinanceSummaryCards';
import TransactionCard from '../components/finance/TransactionCard';
import RecurringTemplateCard from '../components/finance/RecurringTemplateCard';
import { Dialog, Button } from '../components/ui';

import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  type TooltipContentProps,
} from 'recharts';

export default function FinancePage() {
  const [range, setRange] = useState<FinanceRange>('month');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const {
    transactions,
    summary,
    recurringTemplates,
    categories,
    loading,
    error,
    reload: loadData,
  } = useFinanceData(range, categoryFilter || undefined);
  const queryClient = useQueryClient();

  // Form states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formType, setFormType] = useState<'income' | 'expense'>('expense');
  const [formAmount, setFormAmount] = useState<string>('');
  const [formCategory, setFormCategory] = useState<string>('');
  const [formDescription, setFormDescription] = useState<string>('');
  const [formDate, setFormDate] = useState<string>('');
  const [formIsRecurring, setFormIsRecurring] = useState<boolean>(false);
  const [actionError, setActionError] = useState<string | null>(null);
  const [editingTransaction, setEditingTransaction] = useState<Transaction | null>(null);
  const [pendingRemoval, setPendingRemoval] = useState<{
    kind: 'transaction' | 'template';
    id: number;
    label: string;
  } | null>(null);

  const formCategories = categories.filter((category) => category.type === formType);
  const invalidateFinance = async () => {
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: ['finance'] }),
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'finance'] }),
    ]);
  };
  const transactionMutation = useMutation({
    mutationFn: async ({ id, input }: { id?: number; input: TransactionCreateInput | TransactionUpdateInput }) => {
      if (id === undefined) await createTransaction(input as TransactionCreateInput);
      else await updateTransaction(id, input as TransactionUpdateInput);
    },
    onSuccess: async () => {
      setIsModalOpen(false);
      setEditingTransaction(null);
      await invalidateFinance();
    },
    onError: (err: unknown) => setActionError(err instanceof Error ? err.message : 'Не удалось сохранить транзакцию'),
  });
  const removalMutation = useMutation({
    mutationFn: (removal: NonNullable<typeof pendingRemoval>) =>
      removal.kind === 'transaction' ? deleteTransaction(removal.id) : deleteRecurringTemplate(removal.id),
    onSuccess: async () => {
      setPendingRemoval(null);
      await invalidateFinance();
    },
    onError: (err: unknown) => setActionError(err instanceof Error ? err.message : 'Не удалось удалить запись'),
  });
  const submitting = transactionMutation.isPending;

  useEffect(() => {
    if (formCategories.length && !formCategories.some((category) => category.name === formCategory)) {
      setFormCategory(formCategories[0].name);
    }
  }, [formCategories, formCategory]);

  const handleDelete = (id: number) => setPendingRemoval({ kind: 'transaction', id, label: 'Удалить эту операцию?' });
  const handleDeleteTemplate = (id: number) =>
    setPendingRemoval({ kind: 'template', id, label: 'Остановить этот повторяющийся платёж?' });
  const confirmRemoval = async () => {
    if (!pendingRemoval) return;
    removalMutation.mutate(pendingRemoval);
  };

  const handleOpenCreate = () => {
    const todayStr = new Date().toISOString().substring(0, 10);
    setFormType('expense');
    setFormAmount('');
    setFormCategory(categories.find((category) => category.type === 'expense')?.name ?? '');
    setFormDescription('');
    setFormDate(todayStr);
    setFormIsRecurring(false);
    setEditingTransaction(null);
    setActionError(null);
    setIsModalOpen(true);
  };

  const handleOpenEdit = (transaction: Transaction) => {
    setFormType(transaction.type);
    setFormAmount(String(transaction.amount));
    setFormCategory(transaction.category);
    setFormDescription(transaction.description || '');
    setFormDate(transaction.date);
    setFormIsRecurring(false);
    setEditingTransaction(transaction);
    setActionError(null);
    setIsModalOpen(true);
  };

  const closeModal = () => {
    if (submitting) return;
    setIsModalOpen(false);
    setEditingTransaction(null);
  };

  const handleFormSubmit = (e: FormEvent) => {
    e.preventDefault();
    const amountNum = parseFloat(formAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      setActionError('Сумма должна быть положительным числом');
      return;
    }

    if (!formCategory) {
      setActionError('Выберите категорию');
      return;
    }
    const transactionInput = {
      type: formType,
      amount: amountNum,
      category: formCategory,
      description: formDescription.trim() || undefined,
      date: formDate,
    };
    transactionMutation.mutate(
      editingTransaction
        ? { id: editingTransaction.id, input: transactionInput }
        : { input: { ...transactionInput, is_recurring: formIsRecurring } },
    );
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('de-DE', { style: 'currency', currency: 'EUR', minimumFractionDigits: 2 }).format(val);
  };

  const formatDateString = (str: string) => {
    if (!str) return '';
    const dateObj = new Date(str);
    if (isNaN(dateObj.getTime())) return str;
    return dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  const formatCompactDate = (str: string) => {
    const dateObj = new Date(str);
    return Number.isNaN(dateObj.getTime())
      ? str
      : dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long' });
  };

  const periodLabel = summary
    ? summary.start_date === summary.end_date
      ? formatCompactDate(summary.start_date)
      : `${formatCompactDate(summary.start_date)} — ${formatCompactDate(summary.end_date)}`
    : '';

  const visibleTransactions = useMemo(() => {
    const normalizedSearch = searchQuery.trim().toLocaleLowerCase('ru-RU');
    if (!normalizedSearch) return transactions;
    return transactions.filter((transaction) =>
      [transaction.category, transaction.description].some((value) =>
        value.toLocaleLowerCase('ru-RU').includes(normalizedSearch),
      ),
    );
  }, [transactions, searchQuery]);

  const groupedTransactions = useMemo(() => {
    const groups = new Map<string, Transaction[]>();
    visibleTransactions.forEach((transaction) => {
      const group = groups.get(transaction.date) ?? [];
      group.push(transaction);
      groups.set(transaction.date, group);
    });
    return Array.from(groups.entries());
  }, [visibleTransactions]);

  const sortedExpenses = summary ? [...summary.expense_breakdown].sort((a, b) => b.amount - a.amount) : [];
  const largestExpense = sortedExpenses[0];
  const renderExpenseTooltip = ({ active, payload }: TooltipContentProps) => {
    const item = payload[0]?.payload as { category?: string; amount?: number | string } | undefined;
    const amount = Number(item?.amount);
    if (!active || !item || !Number.isFinite(amount)) return null;

    const share = summary && summary.total_expense > 0 ? Math.round((amount / summary.total_expense) * 100) : 0;

    return (
      <div className="min-w-40 rounded-xl border border-rose-500/20 bg-zinc-900/95 px-3.5 py-3 shadow-xl shadow-black/30 backdrop-blur-sm">
        <p className="text-xs font-semibold text-zinc-100">{item.category}</p>
        <div className="mt-2 flex items-baseline justify-between gap-4">
          <span className="text-[10px] font-medium uppercase tracking-wider text-zinc-500">Расходы</span>
          <strong className="font-mono text-sm text-rose-300">{formatCurrency(amount)}</strong>
        </div>
        <p className="mt-1.5 text-[10px] text-zinc-500">{share}% от расходов за период</p>
      </div>
    );
  };

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1 text-[10px] font-semibold text-emerald-300"
            aria-label="Данные финансов хранятся локально"
          >
            <Database className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Локальная база</span>
          </div>
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
                    ? 'bg-emerald-600 text-zinc-100 shadow-md shadow-emerald-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Сегодня
              </button>
              <button
                onClick={() => setRange('week')}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  range === 'week'
                    ? 'bg-emerald-600 text-zinc-100 shadow-md shadow-emerald-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Эта неделя
              </button>
              <button
                onClick={() => setRange('month')}
                className={`flex-1 sm:flex-none px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  range === 'month'
                    ? 'bg-emerald-600 text-zinc-100 shadow-md shadow-emerald-900/30'
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
          {actionError && (
            <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-xs text-rose-200">
              <span>{actionError}</span>
              <button onClick={() => setActionError(null)} className="text-rose-300 hover:text-rose-100">
                Скрыть
              </button>
            </div>
          )}

          {/* Finance summary indicators */}
          {summary && !loading && (
            <FinanceSummaryCards summary={summary} formatCurrency={formatCurrency} periodLabel={periodLabel} />
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
              {summary && sortedExpenses.length > 0 && (
                <div className="rounded-2xl border border-zinc-900 bg-zinc-900/20 p-5">
                  <div className="mb-3 flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="text-xs font-bold uppercase tracking-wider text-zinc-400">
                        Расходы по категориям · {periodLabel}
                      </h3>
                      {largestExpense && (
                        <p className="mt-1 text-xs text-zinc-500">
                          Больше всего: <span className="font-medium text-zinc-300">{largestExpense.category}</span> ·{' '}
                          {formatCurrency(largestExpense.amount)}
                        </p>
                      )}
                    </div>
                    <span className="rounded-lg border border-rose-500/15 bg-rose-500/5 px-2.5 py-1 text-xs font-mono font-semibold text-rose-300">
                      {formatCurrency(summary.total_expense)}
                    </span>
                  </div>
                  <div className="h-[180px] w-full sm:h-[200px]">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart
                        layout="vertical"
                        data={sortedExpenses}
                        margin={{ top: 0, right: 12, left: 0, bottom: 0 }}
                      >
                        <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                        <XAxis type="number" stroke="#71717a" fontSize={10} tickLine={false} axisLine={false} />
                        <YAxis
                          type="category"
                          dataKey="category"
                          width={112}
                          stroke="#a1a1aa"
                          fontSize={10}
                          tickLine={false}
                          axisLine={false}
                        />
                        <Tooltip cursor={false} content={renderExpenseTooltip} />
                        <Bar dataKey="amount" fill="#f43f5e" radius={[0, 5, 5, 0]} barSize={20} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              )}

              {/* Transactions grid */}
              <div>
                <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                  <div>
                    <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">Журнал операций</h3>
                    <p className="mt-1 text-xs text-zinc-600">{periodLabel}</p>
                  </div>
                  <div className="flex flex-col gap-2 sm:flex-row">
                    <label className="relative">
                      <Search className="pointer-events-none absolute left-3 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-zinc-600" />
                      <input
                        value={searchQuery}
                        onChange={(event) => setSearchQuery(event.target.value)}
                        className="w-full rounded-xl border border-zinc-800 bg-zinc-950 py-2 pl-9 pr-3 text-xs text-zinc-200 outline-none focus:border-emerald-500 sm:w-52"
                        placeholder="Поиск по журналу"
                      />
                    </label>
                    <select
                      value={categoryFilter}
                      onChange={(event) => setCategoryFilter(event.target.value)}
                      className="rounded-xl border border-zinc-800 bg-zinc-950 px-3 py-2 text-xs text-zinc-300 outline-none focus:border-emerald-500"
                    >
                      <option value="">Все категории</option>
                      {categories.map((category) => (
                        <option key={category.name} value={category.name}>
                          {category.name}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                {visibleTransactions.length === 0 ? (
                  <div className="w-full max-w-md mx-auto h-32 flex flex-col items-center justify-center gap-2 border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/20 px-6">
                    <p className="text-zinc-500 text-xs">Нет операций по выбранным условиям.</p>
                  </div>
                ) : (
                  <div className="space-y-6">
                    {groupedTransactions.map(([date, dateTransactions]) => (
                      <section key={date}>
                        <h4 className="mb-3 text-xs font-semibold text-zinc-500">{formatDateString(date)}</h4>
                        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
                          {dateTransactions.map((tx) => (
                            <TransactionCard
                              key={tx.id}
                              transaction={tx}
                              formatDate={formatDateString}
                              formatCurrency={formatCurrency}
                              onEdit={handleOpenEdit}
                              onDelete={handleDelete}
                              showDate={false}
                            />
                          ))}
                        </div>
                      </section>
                    ))}
                  </div>
                )}
              </div>

              {/* Recurring subscriptions panel */}
              <div className="border-t border-zinc-900 pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <Repeat className="h-4 w-4 text-emerald-500" />
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                    Запланированные автоплатежи и автодоходы
                  </h3>
                </div>

                {recurringTemplates.length === 0 ? (
                  <div className="w-full h-24 flex items-center justify-center border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/15">
                    <p className="text-zinc-600 text-xs font-sans">Нет запланированных ежемесячных операций.</p>
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
              type="button"
              onClick={closeModal}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors"
              aria-label="Закрыть форму транзакции"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Modal Title */}
            <div>
              <h2 className="text-base font-bold text-zinc-200">
                {editingTransaction ? 'Редактировать транзакцию' : 'Новая транзакция'}
              </h2>
              <p className="text-zinc-500 text-[11px] mt-0.5">
                {editingTransaction
                  ? 'Изменения сразу появятся в журнале финансов.'
                  : 'Заполните форму для добавления операции в журнал финансов'}
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleFormSubmit} className="flex flex-col gap-4.5">
              {/* Type Switcher */}
              <div>
                <span
                  className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5"
                  id="transaction-type-label"
                >
                  Тип транзакции *
                </span>
                <div
                  className="grid grid-cols-2 bg-zinc-950 p-1 border border-zinc-800 rounded-xl"
                  role="group"
                  aria-labelledby="transaction-type-label"
                >
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
                <label
                  htmlFor="transaction-amount"
                  className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5"
                >
                  Сумма (€) *
                </label>
                <input
                  type="number"
                  id="transaction-amount"
                  required
                  step="any"
                  placeholder="0"
                  value={formAmount}
                  onChange={(e) => setFormAmount(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all font-mono"
                />
              </div>

              {/* Category */}
              <div>
                <label
                  htmlFor="transaction-category"
                  className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5"
                >
                  Категория *
                </label>
                <select
                  id="transaction-category"
                  value={formCategory}
                  onChange={(e) => setFormCategory(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 rounded-xl px-4.5 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans cursor-pointer"
                >
                  {formCategories.map((category) => (
                    <option key={category.name} value={category.name}>
                      {category.name}
                    </option>
                  ))}
                </select>
              </div>

              {/* Date */}
              <div>
                <label
                  htmlFor="transaction-date"
                  className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5"
                >
                  Дата операции *
                </label>
                <input
                  type="date"
                  id="transaction-date"
                  required
                  value={formDate}
                  onChange={(e) => setFormDate(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans"
                />
              </div>

              {/* Description */}
              <div>
                <label
                  htmlFor="transaction-description"
                  className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5"
                >
                  Описание
                </label>
                <textarea
                  id="transaction-description"
                  placeholder="Дополнительные детали..."
                  rows={2}
                  value={formDescription}
                  onChange={(e) => setFormDescription(e.target.value)}
                  className="w-full bg-zinc-950 border border-zinc-800 focus:border-emerald-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all resize-none font-sans"
                />
              </div>

              {/* Recurring Switcher */}
              {!editingTransaction && (
                <div className="flex items-center gap-3 bg-zinc-950/40 p-3.5 border border-zinc-800 rounded-xl mt-1.5">
                  <input
                    type="checkbox"
                    id="formIsRecurring"
                    checked={formIsRecurring}
                    onChange={(e) => setFormIsRecurring(e.target.checked)}
                    className="h-4 w-4 bg-zinc-950 border-zinc-800 focus:ring-emerald-500 text-emerald-600 rounded cursor-pointer"
                  />
                  <div
                    className="flex flex-col gap-0.5 cursor-pointer select-none min-w-0"
                    onClick={() => setFormIsRecurring(!formIsRecurring)}
                  >
                    <label
                      htmlFor="formIsRecurring"
                      className="text-xs font-semibold text-zinc-300 flex items-center gap-1.5 cursor-pointer"
                    >
                      <Repeat className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                      Повторять каждый месяц
                    </label>
                    <span className="text-[10px] text-zinc-500 leading-relaxed font-sans">
                      Создаст ежемесячную автоподписку на основе дня выбранной даты.
                    </span>
                  </div>
                </div>
              )}

              {/* Form Actions */}
              <div className="flex gap-3 justify-end border-t border-zinc-800/40 pt-4 mt-1.5">
                <button
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-500 hover:text-zinc-300 hover:bg-zinc-800 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="flex items-center gap-1.5 bg-emerald-600 hover:bg-emerald-500 disabled:bg-emerald-800 active:bg-emerald-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-md shadow-emerald-950/20"
                >
                  {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                  {editingTransaction ? 'Сохранить изменения' : 'Добавить транзакцию'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
      {pendingRemoval && (
        <Dialog
          title={pendingRemoval.label}
          description={
            pendingRemoval.kind === 'template'
              ? 'Новые ежемесячные операции по этому шаблону больше не будут создаваться.'
              : 'Операция будет удалена из журнала финансов.'
          }
          onClose={() => {
            if (!removalMutation.isPending) setPendingRemoval(null);
          }}
        >
          <div className="flex justify-end gap-2">
            <Button disabled={removalMutation.isPending} onClick={() => setPendingRemoval(null)}>
              Отмена
            </Button>
            <Button tone="danger" onClick={confirmRemoval} loading={removalMutation.isPending}>
              Подтвердить
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
