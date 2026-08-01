import { useEffect, useState } from 'react';
import { fetchConsolidationSuggestions, consolidateFacts } from '../api/memory';
import type { ConsolidationSuggestion } from '../api/memory';
import { Merge, ShieldAlert, Check, RefreshCw, X } from 'lucide-react';

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  preference: { bg: 'bg-purple-950/30', text: 'text-purple-300', border: 'border-purple-800/40' },
  habit: { bg: 'bg-emerald-950/30', text: 'text-emerald-300', border: 'border-emerald-800/40' },
  relationship: { bg: 'bg-pink-950/30', text: 'text-pink-300', border: 'border-pink-800/40' },
  project: { bg: 'bg-yellow-950/30', text: 'text-yellow-300', border: 'border-yellow-800/40' },
  other: { bg: 'bg-zinc-800/40', text: 'text-zinc-300', border: 'border-zinc-700/40' },
};

interface ConsolidationQueueProps {
  onConsolidationProcessed: () => void;
}

export default function ConsolidationQueue({ onConsolidationProcessed }: ConsolidationQueueProps) {
  const [suggestions, setSuggestions] = useState<ConsolidationSuggestion[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [processingIndex, setProcessingIndex] = useState<number | null>(null);

  // States to allow user edits of suggestions inline
  const [editedContents, setEditedContents] = useState<Record<number, string>>({});
  const [editedCategories, setEditedCategories] = useState<Record<number, string>>({});
  const [actionError, setActionError] = useState<string | null>(null);

  const errorMessage = (err: unknown, fallback: string) => (err instanceof Error ? err.message : fallback);

  async function loadSuggestions() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchConsolidationSuggestions();
      setSuggestions(data.suggestions || []);

      // Initialize edit states
      const contents: Record<number, string> = {};
      const categories: Record<number, string> = {};
      (data.suggestions || []).forEach((sug, index) => {
        contents[index] = sug.suggested_merged_content;
        categories[index] = sug.category;
      });
      setEditedContents(contents);
      setEditedCategories(categories);
    } catch (err: unknown) {
      setError(errorMessage(err, 'Не удалось загрузить предложения по объединению'));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadSuggestions();
  }, []);

  const handleMerge = async (index: number) => {
    const sug = suggestions[index];
    const finalContent = editedContents[index] || sug.suggested_merged_content;
    const finalCategory = editedCategories[index] || sug.category;

    if (!finalContent.trim()) {
      setActionError('Текст объединённого факта не может быть пустым.');
      return;
    }

    setActionError(null);
    setProcessingIndex(index);
    // Optimistically filter out
    const previousSuggestions = [...suggestions];
    setSuggestions((prev) => prev.filter((_, idx) => idx !== index));

    try {
      await consolidateFacts(sug.fact_ids, finalContent, finalCategory);
      onConsolidationProcessed();
    } catch (err: unknown) {
      setActionError(`Не удалось объединить факты: ${errorMessage(err, 'попробуйте ещё раз')}`);
      setSuggestions(previousSuggestions);
    } finally {
      setProcessingIndex(null);
    }
  };

  const handleSkip = (index: number) => {
    // Simply hide from UI
    setSuggestions((prev) => prev.filter((_, idx) => idx !== index));
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-zinc-400 gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-500 border-t-transparent"></div>
        <span className="text-sm">Поиск семантически похожих фактов через ИИ...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-red-400 max-w-md mx-auto gap-4">
        <ShieldAlert className="h-12 w-12 text-red-500/80" />
        <div>
          <p className="font-semibold text-zinc-200">Ошибка при анализе базы фактов</p>
          <p className="text-xs text-red-500/80 mt-1">{error}</p>
        </div>
        <button
          onClick={loadSuggestions}
          className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          <RefreshCw className="h-3 w-3" /> Попробовать снова
        </button>
      </div>
    );
  }

  if (suggestions.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-16 text-center text-zinc-400 max-w-sm mx-auto">
        <div className="rounded-full bg-zinc-900/80 p-4 border border-zinc-800 mb-4 shadow-inner">
          <Check className="h-8 w-8 text-emerald-500/70" />
        </div>
        <p className="font-medium text-zinc-300">Факты чисты и структурированы</p>
        <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
          ИИ не обнаружил семантически избыточных или дублирующих друг друга фактов. Консолидация не требуется.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-6 py-8 flex flex-col gap-6">
      {actionError && (
        <div className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/5 px-4 py-3 text-xs text-rose-200">
          <span>{actionError}</span>
          <button type="button" onClick={() => setActionError(null)} className="text-rose-300 hover:text-rose-100">
            Закрыть
          </button>
        </div>
      )}
      <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
        <div className="flex items-center gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-500/10 text-xs font-bold text-purple-400 border border-purple-500/20">
            {suggestions.length}
          </span>
          <h2 className="text-lg font-bold text-zinc-200">Рекомендации по консолидации</h2>
        </div>
        <button
          onClick={loadSuggestions}
          className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900 rounded-lg transition-all"
          title="Обновить предложения"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="flex flex-col gap-6">
        {suggestions.map((sug, index) => {
          const contentVal = editedContents[index] ?? sug.suggested_merged_content;
          const categoryVal = editedCategories[index] ?? sug.category;

          return (
            <div
              key={index}
              className="flex flex-col bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-6 shadow-lg backdrop-blur-sm relative overflow-hidden"
            >
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Left side: Source duplicate/similar facts */}
                <div className="flex flex-col border-r border-zinc-800/50 pr-0 lg:pr-6 gap-3">
                  <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
                    Похожие исходные факты:
                  </h3>
                  <div className="flex flex-col gap-3.5 mt-2">
                    {sug.source_facts.map((srcFact) => {
                      const badgeStyle = CATEGORY_COLORS[srcFact.category] || CATEGORY_COLORS.other;
                      return (
                        <div
                          key={srcFact.id}
                          className="flex flex-col bg-zinc-950/40 rounded-xl p-3 border border-zinc-900"
                        >
                          <div className="flex items-center justify-between mb-1.5">
                            <span
                              className={`px-2 py-0.5 rounded text-[8px] font-bold uppercase tracking-wider border ${badgeStyle.bg} ${badgeStyle.text} ${badgeStyle.border}`}
                            >
                              {srcFact.category}
                            </span>
                            <span className="text-[9px] text-zinc-600 font-mono">ID: {srcFact.id}</span>
                          </div>
                          <p className="text-xs text-zinc-300 leading-normal">{srcFact.content}</p>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Right side: Consolidated proposal */}
                <div className="flex flex-col justify-between gap-4">
                  <div className="flex flex-col gap-3">
                    <h3 className="text-xs font-semibold text-zinc-400 uppercase tracking-wide">
                      Предложение по слиянию:
                    </h3>

                    {/* Merged Content Edit */}
                    <div className="flex flex-col gap-1.5 mt-2">
                      <label className="text-[10px] text-zinc-500 font-medium">Объединенная формулировка</label>
                      <textarea
                        value={contentVal}
                        onChange={(e) => setEditedContents((prev) => ({ ...prev, [index]: e.target.value }))}
                        className="w-full bg-zinc-950/80 border border-zinc-800/80 rounded-xl px-4 py-2.5 text-xs text-zinc-100 focus:outline-none focus:border-purple-500/80 shadow-inner font-sans min-h-[70px] resize-y leading-relaxed"
                      />
                    </div>

                    {/* Category Select */}
                    <div className="flex flex-col gap-1.5">
                      <label className="text-[10px] text-zinc-500 font-medium">Категория нового факта</label>
                      <select
                        value={categoryVal}
                        onChange={(e) => setEditedCategories((prev) => ({ ...prev, [index]: e.target.value }))}
                        className="bg-zinc-950 border border-zinc-800/80 rounded-xl px-3 py-1.5 text-xs text-zinc-300 focus:outline-none focus:border-purple-500/80 cursor-pointer"
                      >
                        <option value="preference">Preference (Предпочтение)</option>
                        <option value="habit">Habit (Привычка)</option>
                        <option value="relationship">Relationship (Связь/Отношение)</option>
                        <option value="project">Project (Проект/Хобби)</option>
                        <option value="other">Other (Другое)</option>
                      </select>
                    </div>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center justify-end gap-3 pt-4 border-t border-zinc-800/50 mt-4">
                    <button
                      disabled={processingIndex === index}
                      onClick={() => handleSkip(index)}
                      className="inline-flex items-center justify-center gap-1.5 px-3.5 py-2 bg-zinc-800/60 hover:bg-zinc-800 hover:text-zinc-200 border border-zinc-800 text-zinc-400 rounded-xl text-xs font-semibold transition-all disabled:opacity-50 cursor-pointer"
                    >
                      <X className="h-3.5 w-3.5" /> Не объединять
                    </button>
                    <button
                      disabled={processingIndex === index}
                      onClick={() => handleMerge(index)}
                      className="inline-flex items-center justify-center gap-1.5 px-4 py-2 bg-purple-600 hover:bg-purple-500 active:bg-purple-700 text-zinc-100 rounded-xl text-xs font-semibold shadow-md shadow-purple-950/20 transition-all disabled:opacity-50 cursor-pointer"
                    >
                      <Merge className="h-3.5 w-3.5" /> Объединить факты
                    </button>
                  </div>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
