import { useState, useEffect } from 'react';
import { 
  TrendingUp, 
  TrendingDown, 
  Wallet, 
  Plus, 
  Trash2, 
  Loader2, 
  AlertCircle, 
  X,
  PlusCircle,
  MinusCircle,
  Tag,
  FileText,
  Calendar,
  Repeat
} from 'lucide-react';
import { 
  fetchTransactions, 
  fetchSummary, 
  createTransaction, 
  deleteTransaction, 
  fetchRecurringTemplates,
  deleteRecurringTemplate
} from '../api/finance';
import type { Transaction, FinanceSummary, RecurringTemplate } from '../api/finance';

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
      startStr: dateStr,
      endStr: dateStr
    };
  } else if (range === 'week') {
    const currentDay = now.getDay();
    const distanceToMonday = currentDay === 0 ? 6 : currentDay - 1;
    const monday = new Date(now);
    monday.setDate(now.getDate() - distanceToMonday);
    
    const sunday = new Date(monday);
    sunday.setDate(monday.getDate() + 6);
    
    return {
      startStr: formatLocalDate(monday),
      endStr: formatLocalDate(sunday)
    };
  } else {
    const year = now.getFullYear();
    const month = now.getMonth();
    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    
    return {
      startStr: formatLocalDate(firstDay),
      endStr: formatLocalDate(lastDay)
    };
  }
}

export default function FinancePage() {
  const [range, setRange] = useState<'today' | 'week' | 'month'>('month');
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [summary, setSummary] = useState<FinanceSummary | null>(null);
  const [recurringTemplates, setRecurringTemplates] = useState<RecurringTemplate[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formType, setFormType] = useState<'income' | 'expense'>('expense');
  const [formAmount, setFormAmount] = useState<string>('');
  const [formCategory, setFormCategory] = useState<string>(FINANCE_CATEGORIES[0]);
  const [formDescription, setFormDescription] = useState<string>('');
  const [formDate, setFormDate] = useState<string>('');
  const [formIsRecurring, setFormIsRecurring] = useState<boolean>(false);
  const [submitting, setSubmitting] = useState<boolean>(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const { startStr, endStr } = getRangeDates(range);
      const [txs, sum, templates] = await Promise.all([
        fetchTransactions(startStr, endStr),
        fetchSummary(startStr, endStr),
        fetchRecurringTemplates()
      ]);
      setTransactions(txs);
      setSummary(sum);
      setRecurringTemplates(templates);
    } catch (err: any) {
      setError(err.message || 'Ошибка загрузки финансовых данных');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [range]);

  const handleDelete = async (id: number) => {
    if (!window.confirm('Вы действительно хотите удалить эту операцию?')) {
      return;
    }

    try {
      await deleteTransaction(id);
      loadData();
    } catch (err: any) {
      alert(`Ошибка при удалении: ${err.message}`);
    }
  };

  const handleDeleteTemplate = async (id: number) => {
    if (!window.confirm('Вы действительно хотите остановить эту подписку? Повторяющиеся расходы больше не будут генерироваться.')) {
      return;
    }

    try {
      await deleteRecurringTemplate(id);
      loadData();
    } catch (err: any) {
      alert(`Ошибка при удалении шаблона: ${err.message}`);
    }
  };

  const handleOpenCreate = () => {
    const todayStr = new Date().toISOString().substring(0, 10);
    setFormType('expense');
    setFormAmount('');
    setFormCategory('Еда');
    setFormDescription('');
    setFormDate(todayStr);
    setFormIsRecurring(false);
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const amountNum = parseFloat(formAmount);
    if (isNaN(amountNum) || amountNum <= 0) {
      alert('Сумма должна быть положительным числом');
      return;
    }

    setSubmitting(true);
    try {
      await createTransaction({
        type: formType,
        amount: amountNum,
        category: formCategory,
        description: formDescription,
        date: formDate,
        is_recurring: formIsRecurring
      });
      setIsModalOpen(false);
      loadData();
    } catch (err: any) {
      alert(`Ошибка при сохранении: ${err.message}`);
    } finally {
      setSubmitting(false);
    }
  };

  const formatCurrency = (val: number) => {
    return new Intl.NumberFormat('ru-RU', { style: 'currency', currency: 'RUB', minimumFractionDigits: 0 }).format(val);
  };

  const formatDateString = (str: string) => {
    if (!str) return '';
    const dateObj = new Date(str);
    if (isNaN(dateObj.getTime())) return str;
    return dateObj.toLocaleDateString('ru-RU', { day: 'numeric', month: 'long', year: 'numeric' });
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-emerald-500 shadow-[0_0_8px_#10b981]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Учет Финансов
          </h1>
        </div>

        <div className="text-xs text-zinc-500 font-mono hidden md:block">
          Home Agent Finance API
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

          {/* Finance summary indicators */}
          {summary && !loading && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 w-full">
              {/* Income summary card */}
              <div className="bg-zinc-900/30 border border-zinc-900 rounded-2xl p-4.5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest">Доходы</span>
                  <span className="text-base font-bold text-emerald-400 font-mono">
                    {formatCurrency(summary.total_income)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
                  <TrendingUp className="h-5 w-5" />
                </div>
              </div>

              {/* Expense summary card */}
              <div className="bg-zinc-900/30 border border-zinc-900 rounded-2xl p-4.5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest">Расходы</span>
                  <span className="text-base font-bold text-rose-400 font-mono">
                    {formatCurrency(summary.total_expense)}
                  </span>
                </div>
                <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/10">
                  <TrendingDown className="h-5 w-5" />
                </div>
              </div>

              {/* Net Balance summary card */}
              <div className="bg-zinc-900/30 border border-zinc-900 rounded-2xl p-4.5 flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest">Баланс</span>
                  <span className={`text-base font-bold font-mono ${summary.net_balance >= 0 ? 'text-emerald-400' : 'text-rose-450'}`}>
                    {formatCurrency(summary.net_balance)}
                  </span>
                </div>
                <div className={`p-2.5 rounded-xl border ${summary.net_balance >= 0 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/10' : 'bg-rose-500/10 text-rose-400 border-rose-500/10'}`}>
                  <Wallet className="h-5 w-5" />
                </div>
              </div>
            </div>
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
                      <div 
                        key={tx.id}
                        className="bg-zinc-900/40 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all flex flex-col justify-between group shadow-md hover:shadow-lg"
                      >
                        <div className="flex flex-col gap-3.5">
                          {/* Header: Date and indicator */}
                          <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                            <div className="flex items-center gap-1">
                              <Calendar className="h-3 w-3" />
                              <span>{formatDateString(tx.date)}</span>
                            </div>
                            <span className={`uppercase font-bold px-2 py-0.5 rounded-lg border flex items-center gap-1 ${tx.type === 'income' ? 'text-emerald-400 bg-emerald-500/5 border-emerald-500/10' : 'text-rose-450 bg-rose-500/5 border-rose-500/10'}`}>
                              {tx.type === 'income' ? <PlusCircle className="h-3 w-3" /> : <MinusCircle className="h-3 w-3" />}
                              {tx.type === 'income' ? 'доход' : 'расход'}
                            </span>
                          </div>

                          {/* Amount & Category */}
                          <div className="flex justify-between items-start gap-4">
                            <div className="flex items-center gap-3 min-w-0">
                              <div className={`p-2.5 rounded-xl border shrink-0 ${tx.type === 'income' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25' : 'bg-rose-500/10 text-rose-400 border-rose-500/25'}`}>
                                <Tag className="h-4.5 w-4.5" />
                              </div>
                              <h2 className="text-sm font-semibold text-zinc-200 tracking-wide pr-1 truncate">
                                {tx.category}
                              </h2>
                            </div>
                            <span className={`text-base font-bold font-mono shrink-0 ${tx.type === 'income' ? 'text-emerald-450' : 'text-rose-450'}`}>
                              {tx.type === 'income' ? '+' : '-'}{formatCurrency(tx.amount)}
                            </span>
                          </div>

                          {/* Description */}
                          {tx.description && (
                            <div className="flex gap-2 text-zinc-550 mt-0.5">
                              <FileText className="h-3.5 w-3.5 text-zinc-650 shrink-0 mt-0.5" />
                              <p className="text-xs leading-relaxed font-sans line-clamp-3">
                                {tx.description}
                              </p>
                            </div>
                          )}
                        </div>

                        {/* Actions footer */}
                        <div className="flex justify-end gap-2 border-t border-zinc-800/40 pt-4 mt-5">
                          <button
                            onClick={() => handleDelete(tx.id)}
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

              {/* Recurring subscriptions panel */}
              <div className="border-t border-zinc-900 pt-6">
                <div className="flex items-center gap-2 mb-4">
                  <Repeat className="h-4 w-4 text-emerald-500" />
                  <h3 className="text-xs font-bold text-zinc-400 uppercase tracking-wider">
                    Активные подписки (Ежемесячные шаблоны)
                  </h3>
                </div>
                
                {recurringTemplates.length === 0 ? (
                  <div className="w-full h-24 flex items-center justify-center border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/15">
                    <p className="text-zinc-600 text-xs font-sans">Нет ежемесячных подписок.</p>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {recurringTemplates.map((template) => (
                      <div 
                        key={template.id}
                        className="bg-zinc-900/20 border border-zinc-900 rounded-2xl p-4.5 flex flex-col justify-between hover:border-zinc-800/60 transition-all shadow-sm"
                      >
                        <div className="flex flex-col gap-2.5">
                          <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                            <span>Каждое {template.day_of_month} число месяца</span>
                            <span className="uppercase text-emerald-555 font-bold bg-emerald-500/5 px-2 py-0.5 rounded-lg border border-emerald-500/10 flex items-center gap-0.5">
                              <Repeat className="h-2.5 w-2.5" />
                              Авто
                            </span>
                          </div>

                          <div className="flex justify-between items-center gap-3">
                            <div className="flex items-center gap-2 min-w-0">
                              <div className="p-2 rounded-xl bg-zinc-800/40 text-zinc-450 shrink-0">
                                <Tag className="h-4 w-4" />
                              </div>
                              <span className="text-xs font-semibold text-zinc-350 truncate pr-1">
                                {template.category}
                              </span>
                            </div>
                            <span className="text-xs font-bold text-rose-400 font-mono shrink-0">
                              -{formatCurrency(template.amount)}
                            </span>
                          </div>

                          {template.description && (
                            <p className="text-xs text-zinc-550 line-clamp-1 italic font-sans pl-8">
                              {template.description}
                            </p>
                          )}
                        </div>

                        <div className="flex justify-end border-t border-zinc-800/30 pt-3 mt-4">
                          <button
                            onClick={() => handleDeleteTemplate(template.id)}
                            className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
                            title="Остановить автоплатеж"
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </button>
                        </div>
                      </div>
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
                  Сумма (₽) *
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
                    Повторять каждый месяц
                  </label>
                  <span className="text-[10px] text-zinc-550 leading-relaxed font-sans">
                    Создаст ежемесячную автоподписку на основе дня выбранной даты.
                  </span>
                </div>
              </div>

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
    </div>
  );
}
