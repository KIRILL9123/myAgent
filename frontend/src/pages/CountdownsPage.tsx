import { useState, useEffect, type FormEvent } from 'react';
import { Clock, Plus, Trash2, Loader2, AlertCircle, AlertTriangle, Compass, Briefcase, Smile, Tag } from 'lucide-react';
import { fetchCountdowns, createCountdown, deleteCountdown } from '../api/countdown';
import type { Countdown } from '../api/countdown';
import { Button, Dialog } from '../components/ui';

const COUNTDOWN_CATEGORIES = [
  { name: 'работа', label: 'Работа', icon: Briefcase, color: '#facc15' },
  { name: 'личное', label: 'Личное', icon: Smile, color: '#f472b6' },
  { name: 'авто', label: 'Автомобиль', icon: Compass, color: '#38bdf8' },
  { name: 'другое', label: 'Другое', icon: Tag, color: '#a1a1aa' },
];

export default function CountdownsPage() {
  const [countdowns, setCountdowns] = useState<Countdown[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Form states
  const [isModalOpen, setIsModalOpen] = useState<boolean>(false);
  const [formTitle, setFormTitle] = useState<string>('');
  const [formDate, setFormDate] = useState<string>('');
  const [formCategory, setFormCategory] = useState<string>('другое');
  const [submitting, setSubmitting] = useState<boolean>(false);
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);

  const errorMessage = (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchCountdowns();
      setCountdowns(data);
    } catch (err: unknown) {
      setError(errorMessage(err, 'Ошибка загрузки дедлайнов'));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const confirmDelete = async () => {
    if (pendingDeleteId === null) return;
    const id = pendingDeleteId;
    setActionError(null);
    try {
      await deleteCountdown(id);
      setPendingDeleteId(null);
      loadData();
    } catch (err: unknown) {
      setActionError(`Не удалось удалить дедлайн: ${errorMessage(err, 'попробуйте ещё раз')}`);
    }
  };

  const handleOpenCreate = () => {
    const todayStr = new Date().toISOString().substring(0, 10);
    setFormTitle('');
    setFormDate(todayStr);
    setFormCategory('другое');
    setIsModalOpen(true);
  };

  const handleFormSubmit = async (e: FormEvent) => {
    e.preventDefault();
    if (!formTitle.trim() || !formDate) return;

    setSubmitting(true);
    try {
      await createCountdown({
        title: formTitle,
        target_date: formDate,
        category: formCategory,
      });
      setIsModalOpen(false);
      loadData();
    } catch (err: unknown) {
      setActionError(`Не удалось создать дедлайн: ${errorMessage(err, 'попробуйте ещё раз')}`);
    } finally {
      setSubmitting(false);
    }
  };

  const getCategoryIcon = (catName: string) => {
    const found = COUNTDOWN_CATEGORIES.find((c) => c.name === catName.toLowerCase());
    return found ? found.icon : Tag;
  };

  const getCategoryColor = (catName: string) => {
    const found = COUNTDOWN_CATEGORIES.find((c) => c.name === catName.toLowerCase());
    return found ? found.color : '#a1a1aa';
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
          <div className="h-3 w-3 animate-pulse rounded-full bg-rose-500 shadow-[0_0_8px_#f43f5e]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Дедлайны и События
          </h1>
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 overflow-y-auto w-full h-full flex flex-col">
        {/* Controls Bar */}
        <div className="flex justify-between items-center px-6 py-5 bg-zinc-950/40 border-b border-zinc-900 shrink-0">
          <span className="text-xs text-zinc-500 font-medium">Список отсортирован по дате наступления</span>

          <button
            onClick={handleOpenCreate}
            className="flex items-center justify-center gap-2 bg-rose-600 hover:bg-rose-500 active:bg-rose-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-lg shadow-rose-950/20"
          >
            <Plus className="h-4 w-4" />
            Добавить дедлайн
          </button>
        </div>

        {/* Display Content Area */}
        <div className="flex-1 w-full p-6">
          {actionError && (
            <div className="mb-4 flex items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-xs text-rose-200">
              <span>{actionError}</span>
              <button type="button" onClick={() => setActionError(null)} className="text-rose-300 hover:text-rose-100">
                Закрыть
              </button>
            </div>
          )}
          {loading ? (
            <div className="w-full h-64 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-rose-500" />
              <span className="text-zinc-500 text-xs font-medium">Расчет оставшихся дней...</span>
            </div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/20 text-red-200 text-xs px-5 py-4 rounded-xl flex items-center gap-3 max-w-xl mx-auto mt-6">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <div className="flex-1">
                <span className="font-bold">Ошибка:</span> {error}
              </div>
              <button
                onClick={loadData}
                className="bg-red-950/40 hover:bg-red-900/40 text-red-300 font-semibold px-3 py-1.5 rounded-lg text-[10px] tracking-wide transition-all uppercase border border-red-500/20"
              >
                Повторить
              </button>
            </div>
          ) : countdowns.length === 0 ? (
            <div className="w-full max-w-md mx-auto h-64 flex flex-col items-center justify-center gap-4 text-center border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/20 px-6 mt-6">
              <Clock className="h-10 w-10 text-zinc-600" />
              <div>
                <h3 className="text-sm font-semibold text-zinc-300">Дедлайны отсутствуют</h3>
                <p className="text-zinc-500 text-xs mt-1">У вас нет запланированных крайних сроков в системе.</p>
              </div>
              <button
                onClick={handleOpenCreate}
                className="text-xs font-semibold text-rose-400 hover:text-rose-300 transition-colors"
              >
                Создать дедлайн
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {countdowns.map((cd) => {
                const CatIcon = getCategoryIcon(cd.category);
                const catColor = getCategoryColor(cd.category);

                // Color card dynamically if urgent (days_remaining < 30)
                const isUrgent = cd.days_remaining <= 30 && cd.days_remaining >= 0;
                const isPast = cd.days_remaining < 0;

                return (
                  <div
                    key={cd.id}
                    className={`border hover:border-zinc-800/80 rounded-2xl p-5 transition-all flex flex-col justify-between group shadow-md hover:shadow-lg ${
                      isUrgent
                        ? 'bg-rose-950/35 border-rose-500/25 hover:border-rose-500/40'
                        : isPast
                          ? 'bg-zinc-950/40 border-zinc-950 opacity-60'
                          : 'bg-zinc-900/40 border-zinc-900 hover:border-zinc-800/80'
                    }`}
                  >
                    <div className="flex flex-col gap-4">
                      {/* Header: Category Badge and Days remaining badge */}
                      <div className="flex justify-between items-center">
                        {/* Category tag */}
                        <div
                          className="flex items-center gap-1.5 px-2.5 py-0.5 rounded-lg border text-[10px] font-bold uppercase tracking-wider"
                          style={{ borderColor: `${catColor}20`, color: catColor, backgroundColor: `${catColor}08` }}
                        >
                          <CatIcon className="h-3 w-3" />
                          <span>{cd.category}</span>
                        </div>

                        {/* Days remaining badge */}
                        <div
                          className={`px-2 py-0.5 rounded-lg border text-[10px] font-bold font-mono ${
                            isUrgent
                              ? 'text-rose-400 bg-rose-500/10 border-rose-500/20 flex items-center gap-1'
                              : isPast
                                ? 'text-zinc-500 bg-zinc-950 border-zinc-900'
                                : 'text-zinc-300 bg-zinc-800 border-zinc-700'
                          }`}
                        >
                          {isUrgent && <AlertTriangle className="h-3 w-3 animate-pulse text-rose-400 shrink-0" />}
                          {isPast
                            ? 'просрочено'
                            : `осталось: ${cd.days_remaining} ${
                                cd.days_remaining % 10 === 1 && cd.days_remaining % 100 !== 11
                                  ? 'день'
                                  : [2, 3, 4].includes(cd.days_remaining % 10) &&
                                      ![12, 13, 14].includes(cd.days_remaining % 100)
                                    ? 'дня'
                                    : 'дней'
                              }`}
                        </div>
                      </div>

                      {/* Title & Target Date */}
                      <div className="flex flex-col gap-2 min-w-0">
                        <h2 className="text-sm font-semibold text-zinc-200 tracking-wide line-clamp-2 pr-2">
                          {cd.title}
                        </h2>

                        {/* Target Date text */}
                        <div className="flex items-center gap-2 text-zinc-500 mt-0.5">
                          <Clock className="h-3.5 w-3.5 text-zinc-600 shrink-0" />
                          <span className="text-[11px] font-medium leading-none">
                            {formatDateString(cd.target_date)}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Actions footer */}
                    <div className="flex justify-end gap-2 border-t border-zinc-800/40 pt-4 mt-5">
                      <button
                        onClick={() => {
                          setActionError(null);
                          setPendingDeleteId(cd.id);
                        }}
                        className="p-2 rounded-xl text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20"
                        title="Удалить"
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {isModalOpen && (
        <Dialog
          title="Новый дедлайн"
          description="Добавьте дату, чтобы агент мог вовремя напомнить о событии."
          onClose={() => setIsModalOpen(false)}
        >
          <form onSubmit={handleFormSubmit} className="flex flex-col gap-4">
            {/* Title */}
            <div>
              <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                Название события *
              </label>
              <input
                type="text"
                required
                placeholder="Например: Сдача проекта Ausbildung"
                value={formTitle}
                onChange={(e) => setFormTitle(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 focus:border-rose-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all"
              />
            </div>

            {/* Target Date */}
            <div>
              <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                Целевая дата *
              </label>
              <input
                type="date"
                required
                value={formDate}
                onChange={(e) => setFormDate(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 focus:border-rose-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans"
              />
            </div>

            {/* Category select */}
            <div>
              <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                Категория *
              </label>
              <select
                value={formCategory}
                onChange={(e) => setFormCategory(e.target.value)}
                className="w-full bg-zinc-950 border border-zinc-800 focus:border-rose-500 rounded-xl px-4.5 py-2.5 text-xs text-zinc-100 focus:outline-none transition-all font-sans cursor-pointer"
              >
                {COUNTDOWN_CATEGORIES.map((cat) => (
                  <option key={cat.name} value={cat.name}>
                    {cat.label}
                  </option>
                ))}
              </select>
            </div>

            {/* Form Actions */}
            <div className="flex gap-3 justify-end border-t border-zinc-800/40 pt-4 mt-1.5">
              <button
                type="button"
                onClick={() => setIsModalOpen(false)}
                className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800 transition-colors"
              >
                Отмена
              </button>
              <button
                type="submit"
                disabled={submitting}
                className="flex items-center gap-1.5 bg-rose-600 hover:bg-rose-500 disabled:bg-rose-800 active:bg-rose-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-md shadow-rose-950/20"
              >
                {submitting && <Loader2 className="h-3.5 w-3.5 animate-spin" />}
                Добавить дедлайн
              </button>
            </div>
          </form>
        </Dialog>
      )}
      {pendingDeleteId !== null && (
        <Dialog
          title="Удалить дедлайн?"
          description="Запись будет удалена из списка и не попадёт в будущие напоминания."
          onClose={() => setPendingDeleteId(null)}
        >
          <div className="flex justify-end gap-2">
            <Button onClick={() => setPendingDeleteId(null)}>Отмена</Button>
            <Button tone="danger" onClick={confirmDelete}>
              Удалить
            </Button>
          </div>
        </Dialog>
      )}
    </div>
  );
}
