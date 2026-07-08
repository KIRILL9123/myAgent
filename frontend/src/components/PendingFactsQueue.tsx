import { useEffect, useState } from 'react';
import { fetchPendingFacts, approveFact, rejectFact } from '../api/memory';
import type { PendingFact } from '../api/memory';
import { Check, Trash2, AlertCircle, RefreshCw } from 'lucide-react';

const CATEGORY_COLORS: Record<string, { bg: string; text: string; border: string }> = {
  preference: { bg: 'bg-purple-950/30', text: 'text-purple-300', border: 'border-purple-800/40' },
  habit: { bg: 'bg-emerald-950/30', text: 'text-emerald-300', border: 'border-emerald-800/40' },
  relationship: { bg: 'bg-pink-950/30', text: 'text-pink-300', border: 'border-pink-800/40' },
  project: { bg: 'bg-yellow-950/30', text: 'text-yellow-300', border: 'border-yellow-800/40' },
  other: { bg: 'bg-zinc-800/40', text: 'text-zinc-300', border: 'border-zinc-700/40' },
};

interface PendingFactsQueueProps {
  onFactProcessed: () => void;
}

export default function PendingFactsQueue({ onFactProcessed }: PendingFactsQueueProps) {
  const [facts, setFacts] = useState<PendingFact[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [processingId, setProcessingId] = useState<number | null>(null);

  async function loadPending() {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchPendingFacts();
      setFacts(data.facts || []);
    } catch (err: any) {
      setError(err.message || 'Не удалось загрузить очередь подтверждения');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadPending();
  }, []);

  const handleApprove = async (id: number) => {
    setProcessingId(id);
    // Optimistic UI update: hold previous state in case of error
    const previousFacts = [...facts];
    setFacts((prev) => prev.filter((f) => f.id !== id));

    try {
      await approveFact(id);
      onFactProcessed();
    } catch (err: any) {
      alert(`Ошибка при подтверждении факта: ${err.message}`);
      // Rollback optimistic update
      setFacts(previousFacts);
    } finally {
      setProcessingId(null);
    }
  };

  const handleReject = async (id: number) => {
    if (!confirm('Вы уверены, что хотите отклонить этот факт?')) return;
    setProcessingId(id);
    const previousFacts = [...facts];
    setFacts((prev) => prev.filter((f) => f.id !== id));

    try {
      await rejectFact(id);
      onFactProcessed();
    } catch (err: any) {
      alert(`Ошибка при отклонении факта: ${err.message}`);
      setFacts(previousFacts);
    } finally {
      setProcessingId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-zinc-400 gap-4">
        <div className="h-8 w-8 animate-spin rounded-full border-4 border-purple-500 border-t-transparent"></div>
        <span className="text-sm">Загрузка очереди подтверждения...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center p-8 text-center text-red-400 max-w-md mx-auto gap-4">
        <AlertCircle className="h-12 w-12 text-red-500/80" />
        <div>
          <p className="font-semibold text-zinc-200">Ошибка при получении данных</p>
          <p className="text-xs text-red-500/80 mt-1">{error}</p>
        </div>
        <button
          onClick={loadPending}
          className="inline-flex items-center gap-2 rounded-lg bg-zinc-900 border border-zinc-800 px-4 py-2 text-xs font-semibold text-zinc-300 hover:bg-zinc-800 transition-colors"
        >
          <RefreshCw className="h-3 w-3" /> Попробовать снова
        </button>
      </div>
    );
  }

  if (facts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-16 text-center text-zinc-400 max-w-sm mx-auto">
        <div className="rounded-full bg-zinc-900/80 p-4 border border-zinc-800 mb-4 shadow-inner">
          <Check className="h-8 w-8 text-emerald-500/70" />
        </div>
        <p className="font-medium text-zinc-300">Всё чисто!</p>
        <p className="text-xs text-zinc-500 mt-1 leading-relaxed">
          Нет новых фактов, ожидающих подтверждения. Все извлеченные факты уже обработаны.
        </p>
      </div>
    );
  }

  return (
    <div className="w-full max-w-4xl mx-auto px-6 py-8 flex flex-col gap-6">
      <div className="flex items-center justify-between border-b border-zinc-900 pb-4">
        <div className="flex items-center gap-3">
          <span className="flex h-6 w-6 items-center justify-center rounded-full bg-purple-500/10 text-xs font-bold text-purple-400 border border-purple-500/20">
            {facts.length}
          </span>
          <h2 className="text-lg font-bold text-zinc-200">Факты на подтверждение</h2>
        </div>
        <button
          onClick={loadPending}
          className="p-2 text-zinc-500 hover:text-zinc-300 hover:bg-zinc-900 rounded-lg transition-all"
          title="Обновить список"
        >
          <RefreshCw className="h-4 w-4" />
        </button>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {facts.map((fact) => {
          const categoryStyle = CATEGORY_COLORS[fact.category] || CATEGORY_COLORS.other;
          const confidencePercent = Math.round(fact.confidence * 100);

          return (
            <div
              key={fact.id}
              className="flex flex-col bg-zinc-900/60 border border-zinc-800/80 rounded-2xl p-5 shadow-lg backdrop-blur-sm transition-all hover:border-zinc-700/80 hover:shadow-xl relative overflow-hidden"
            >
              {/* Top Row Category & Confidence */}
              <div className="flex items-center justify-between mb-4">
                <span
                  className={`inline-flex items-center rounded-md px-2.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider border ${categoryStyle.bg} ${categoryStyle.text} ${categoryStyle.border}`}
                >
                  {fact.category}
                </span>
                <span className="text-[10px] text-zinc-500 font-mono">
                  ID: {fact.id}
                </span>
              </div>

              {/* Main content */}
              <p className="text-sm font-medium text-zinc-200 leading-relaxed flex-grow mb-6">
                {fact.content}
              </p>

              {/* Confidence Progress bar */}
              <div className="flex flex-col gap-1.5 mb-6">
                <div className="flex items-center justify-between text-[11px]">
                  <span className="text-zinc-500 font-medium">Достоверность ИИ</span>
                  <span className="text-purple-400 font-semibold font-mono">{confidencePercent}%</span>
                </div>
                <div className="w-full bg-zinc-800 rounded-full h-1.5 overflow-hidden">
                  <div
                    className="h-1.5 rounded-full bg-gradient-to-r from-purple-500 to-indigo-500 transition-all duration-500"
                    style={{ width: `${confidencePercent}%` }}
                  ></div>
                </div>
              </div>

              {/* Footer Buttons & Date */}
              <div className="flex items-center justify-between pt-4 border-t border-zinc-800/50 mt-auto">
                <span className="text-[10px] text-zinc-600 font-mono">
                  {new Date(fact.created_at).toLocaleDateString('ru-RU')}
                </span>
                
                <div className="flex items-center gap-2">
                  <button
                    disabled={processingId === fact.id}
                    onClick={() => handleReject(fact.id)}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-zinc-800 hover:bg-rose-950/30 hover:text-rose-400 hover:border-rose-900/30 border border-zinc-800 text-zinc-400 rounded-lg text-xs font-semibold transition-all disabled:opacity-50"
                  >
                    <Trash2 className="h-3.5 w-3.5" /> Отклонить
                  </button>
                  <button
                    disabled={processingId === fact.id}
                    onClick={() => handleApprove(fact.id)}
                    className="inline-flex items-center justify-center gap-1.5 px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 active:bg-emerald-700 text-zinc-100 rounded-lg text-xs font-semibold shadow-md shadow-emerald-950/20 transition-all disabled:opacity-50"
                  >
                    <Check className="h-3.5 w-3.5" /> Подтвердить
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
