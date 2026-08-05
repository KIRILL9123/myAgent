import { TrendingDown, TrendingUp, Wallet } from 'lucide-react';
import type { FinanceSummary } from '../../types';

interface FinanceSummaryCardsProps {
  summary: FinanceSummary;
  formatCurrency: (value: number, currency?: string) => string;
}

export default function FinanceSummaryCards({ summary, formatCurrency }: FinanceSummaryCardsProps) {
  const currency = summary.display_currency || summary.currency || 'EUR';
  return (
    <div className="w-full">
      {summary.mixed_currency && (
        <div className="mb-3 rounded-xl border border-amber-500/20 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200">
          В журнале несколько валют. Итоги показаны отдельно; конвертация не выполняется.
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
      <div className="bg-zinc-900/30 border border-zinc-900 rounded-2xl p-4.5 flex items-center justify-between">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest">Доходы</span>
          <span className="text-base font-bold text-emerald-400 font-mono">
            {formatCurrency(summary.total_income, currency)}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-emerald-500/10 text-emerald-400 border border-emerald-500/10">
          <TrendingUp className="h-5 w-5" />
        </div>
      </div>

      <div className="flex min-w-0 items-center justify-between rounded-2xl border border-zinc-900 bg-zinc-900/30 p-4.5">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest">Расходы</span>
          <span className="text-base font-bold text-rose-400 font-mono">
            {formatCurrency(summary.total_expense, currency)}
          </span>
        </div>
        <div className="p-2.5 rounded-xl bg-rose-500/10 text-rose-400 border border-rose-500/10">
          <TrendingDown className="h-5 w-5" />
        </div>
      </div>

      <div className="flex min-w-0 items-center justify-between rounded-2xl border border-zinc-900 bg-zinc-900/30 p-4.5">
        <div className="flex flex-col gap-1">
          <span className="text-[10px] font-bold text-zinc-550 uppercase tracking-widest">Баланс</span>
          <span className={`text-base font-bold font-mono ${summary.net_balance >= 0 ? 'text-emerald-400' : 'text-rose-450'}`}>
            {formatCurrency(summary.net_balance, currency)}
          </span>
        </div>
        <div
          className={`p-2.5 rounded-xl border ${summary.net_balance >= 0 ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/10' : 'bg-rose-500/10 text-rose-400 border-rose-500/10'}`}
        >
          <Wallet className="h-5 w-5" />
        </div>
      </div>
      </div>
    </div>
  );
}
