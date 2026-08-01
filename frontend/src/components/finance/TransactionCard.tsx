import { Calendar, Edit3, FileText, MinusCircle, PlusCircle, Tag, Trash2 } from 'lucide-react';
import type { Transaction } from '../../types';

interface TransactionCardProps {
  transaction: Transaction;
  formatDate: (value: string) => string;
  formatCurrency: (value: number) => string;
  onEdit: (transaction: Transaction) => void;
  onDelete: (id: number) => void;
}

export default function TransactionCard({ transaction, formatDate, formatCurrency, onEdit, onDelete }: TransactionCardProps) {
  const isIncome = transaction.type === 'income';

  return (
    <div className="bg-zinc-900/40 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all flex flex-col justify-between group shadow-md hover:shadow-lg">
      <div className="flex flex-col gap-3.5">
        <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>{formatDate(transaction.date)}</span>
          </div>
          <span className={`uppercase font-bold px-2 py-0.5 rounded-lg border flex items-center gap-1 ${isIncome ? 'text-emerald-400 bg-emerald-500/5 border-emerald-500/10' : 'text-rose-400 bg-rose-500/5 border-rose-500/10'}`}>
            {isIncome ? <PlusCircle className="h-3 w-3" /> : <MinusCircle className="h-3 w-3" />}
            {isIncome ? 'доход' : 'расход'}
          </span>
        </div>

        <div className="flex justify-between items-start gap-4">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`p-2.5 rounded-xl border shrink-0 ${isIncome ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/25' : 'bg-rose-500/10 text-rose-400 border-rose-500/25'}`}>
              <Tag className="h-4.5 w-4.5" />
            </div>
            <h2 className="text-sm font-semibold text-zinc-200 tracking-wide pr-1 truncate">
              {transaction.category}
            </h2>
          </div>
          <span className={`text-base font-bold font-mono shrink-0 ${isIncome ? 'text-emerald-400' : 'text-rose-400'}`}>
            {isIncome ? '+' : '-'}{formatCurrency(transaction.amount)}
          </span>
        </div>

        {transaction.description && (
          <div className="flex gap-2 text-zinc-500 mt-0.5">
            <FileText className="h-3.5 w-3.5 text-zinc-600 shrink-0 mt-0.5" />
            <p className="text-xs leading-relaxed font-sans line-clamp-3">{transaction.description}</p>
          </div>
        )}
      </div>

      <div className="flex justify-end gap-2 border-t border-zinc-800/40 pt-4 mt-5">
        <button
          onClick={() => onEdit(transaction)}
          className="inline-flex items-center gap-1.5 rounded-xl border border-zinc-800 px-3 py-2 text-[11px] font-semibold text-zinc-400 transition-all hover:border-emerald-500/30 hover:bg-emerald-500/10 hover:text-emerald-300"
          aria-label={`Редактировать операцию: ${transaction.category}`}
        >
          <Edit3 className="h-3.5 w-3.5" />
          Изменить
        </button>
        <button
          onClick={() => onDelete(transaction.id)}
          className="p-2 rounded-xl text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all border border-transparent hover:border-red-500/20"
          title="Удалить"
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
