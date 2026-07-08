import { useState } from 'react';
import MemoryGraph from '../components/MemoryGraph';
import PendingFactsQueue from '../components/PendingFactsQueue';
import ConsolidationQueue from '../components/ConsolidationQueue';
import { backfillRelations } from '../api/memory';

const CATEGORY_LEGEND = [
  { name: 'preference', label: 'Предпочтения (preference)', color: '#c084fc' },
  { name: 'habit', label: 'Привычки (habit)', color: '#4ade80' },
  { name: 'relationship', label: 'Связи/Контакты (relationship)', color: '#f472b6' },
  { name: 'project', label: 'Проекты (project)', color: '#facc15' },
  { name: 'other', label: 'Другое (other)', color: '#a1a1aa' },
];

const RELATION_LEGEND = [
  { label: 'Связано (related_to)', color: '#475569', style: 'border-solid' },
  { label: 'Противоречит (contradicts)', color: '#ef4444', style: 'border-dashed' },
  { label: 'Уточняет (clarifies)', color: '#38bdf8', style: 'border-solid' },
  { label: 'Причина (causes)', color: '#34d399', style: 'border-solid', particles: true },
];

export default function MemoryPage() {
  const [activeTab, setActiveTab] = useState<'graph' | 'pending' | 'consolidate'>('graph');
  const [refreshTrigger, setRefreshTrigger] = useState<number>(0);
  const [backfilling, setBackfilling] = useState<boolean>(false);

  const handleRefresh = () => setRefreshTrigger((prev) => prev + 1);

  const handleBackfill = async () => {
    setBackfilling(true);
    try {
      const result = await backfillRelations();
      alert(`Пересчет связей завершен! Добавлено новых связей: ${result.relations_added}`);
      handleRefresh();
    } catch (err: any) {
      alert(`Ошибка при пересчете связей: ${err.message}`);
    } finally {
      setBackfilling(false);
    }
  };

  return (
    <div className="h-screen w-screen flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-purple-500 shadow-[0_0_8px_#a855f7]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Карта памяти пользователя
          </h1>
        </div>

        {/* Navigation Tabs */}
        <div className="flex bg-zinc-900 border border-zinc-800/80 rounded-xl p-1 font-sans">
          <button
            onClick={() => setActiveTab('graph')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === 'graph'
                ? 'bg-purple-600 text-zinc-100 shadow-md shadow-purple-900/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Граф памяти
          </button>
          <button
            onClick={() => setActiveTab('pending')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === 'pending'
                ? 'bg-purple-600 text-zinc-100 shadow-md shadow-purple-900/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            На подтверждение
          </button>
          <button
            onClick={() => setActiveTab('consolidate')}
            className={`px-4 py-1.5 rounded-lg text-xs font-semibold tracking-wide transition-all ${
              activeTab === 'consolidate'
                ? 'bg-purple-600 text-zinc-100 shadow-md shadow-purple-900/30'
                : 'text-zinc-400 hover:text-zinc-200'
            }`}
          >
            Консолидация
          </button>
        </div>

        <div className="text-xs text-zinc-500 font-mono hidden md:block">
          Home Agent Memory Layer
        </div>
      </header>

      {/* Main Container */}
      <main className="flex-1 relative w-full h-full overflow-y-auto">
        {activeTab === 'graph' ? (
          <>
            {/* Force Directed Graph */}
            <MemoryGraph refreshTrigger={refreshTrigger} />
            
            {/* Legend layout */}
            <div className="absolute top-6 right-6 bg-zinc-900/80 border border-zinc-800 rounded-2xl p-5 shadow-2xl backdrop-blur-md z-10 w-72 text-sm flex flex-col gap-5 select-none pointer-events-auto">
              <div>
                <h2 className="font-semibold text-zinc-200 border-b border-zinc-800 pb-2 mb-3">
                  Категории фактов
                </h2>
                <ul className="flex flex-col gap-2.5">
                  {CATEGORY_LEGEND.map((item) => (
                    <li key={item.name} className="flex items-center gap-3 text-xs text-zinc-400">
                      <span
                        className="h-3.5 w-3.5 rounded-full flex-shrink-0 border border-black/40 shadow-sm"
                        style={{ backgroundColor: item.color }}
                      ></span>
                      <span>{item.label}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div>
                <h2 className="font-semibold text-zinc-200 border-b border-zinc-800 pb-2 mb-3">
                  Типы связей
                </h2>
                <ul className="flex flex-col gap-2.5">
                  {RELATION_LEGEND.map((item, idx) => (
                    <li key={idx} className="flex items-center gap-3 text-xs text-zinc-400">
                      <span
                        className="w-8 h-0.5 border-t flex-shrink-0 relative"
                        style={{
                          borderColor: item.color,
                          borderStyle: item.style === 'border-dashed' ? 'dashed' : 'solid',
                          borderWidth: '2px',
                        }}
                      >
                        {item.particles && (
                          <span
                            className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 h-1.5 w-1.5 rounded-full animate-ping"
                            style={{ backgroundColor: item.color }}
                          ></span>
                        )}
                      </span>
                      <span>{item.label}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {/* Backfill Button */}
              <div className="border-t border-zinc-800 pt-3 flex flex-col gap-3">
                <button
                  disabled={backfilling}
                  onClick={handleBackfill}
                  className="w-full py-2 px-3 bg-zinc-800 border border-zinc-700 hover:bg-zinc-700 hover:border-zinc-600 active:bg-zinc-950 text-zinc-200 rounded-xl text-xs font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
                >
                  {backfilling ? (
                    <span className="h-3.5 w-3.5 animate-spin rounded-full border border-zinc-400 border-t-transparent"></span>
                  ) : (
                    <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 1121.21 8H12M4 9h5" />
                    </svg>
                  )}
                  <span>{backfilling ? 'Пересчет...' : 'Пересчитать связи'}</span>
                </button>
              </div>

              <div className="text-[10px] text-zinc-500 leading-normal border-t border-zinc-800 pt-3">
                <p>💡 Подсказка:</p>
                <p className="mt-1">
                  Перетаскивайте узлы мышкой для изменения структуры графа. Кликните на узел для детального просмотра.
                </p>
              </div>
            </div>
          </>
        ) : activeTab === 'pending' ? (
          <PendingFactsQueue onFactProcessed={handleRefresh} />
        ) : (
          <ConsolidationQueue onConsolidationProcessed={handleRefresh} />
        )}
      </main>
    </div>
  );
}
