import { Repeat, Tag, Trash2 } from 'lucide-react';
import type { RecurringTemplate } from '../../types';

interface RecurringTemplateCardProps {
  template: RecurringTemplate;
  formatCurrency: (value: number) => string;
  onDelete: (id: number) => void;
}

export default function RecurringTemplateCard({ template, formatCurrency, onDelete }: RecurringTemplateCardProps) {
  return (
    <div className="bg-zinc-900/20 border border-zinc-900 rounded-2xl p-4.5 flex flex-col justify-between hover:border-zinc-800/60 transition-all shadow-sm">
      <div className="flex flex-col gap-2.5">
        <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
          <span>Каждое {template.day_of_month} число месяца</span>
          <span className="uppercase text-emerald-500 font-bold bg-emerald-500/5 px-2 py-0.5 rounded-lg border border-emerald-500/10 flex items-center gap-0.5">
            <Repeat className="h-2.5 w-2.5" />
            Авто
          </span>
        </div>

        <div className="flex justify-between items-center gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-2 rounded-xl bg-zinc-800/40 text-zinc-500 shrink-0">
              <Tag className="h-4 w-4" />
            </div>
            <span className="text-xs font-semibold text-zinc-400 truncate pr-1">{template.category}</span>
          </div>
          <span className="text-xs font-bold text-rose-400 font-mono shrink-0">-{formatCurrency(template.amount)}</span>
        </div>

        {template.description && (
          <p className="text-xs text-zinc-500 line-clamp-1 italic font-sans pl-8">{template.description}</p>
        )}
      </div>

      <div className="flex justify-end border-t border-zinc-800/30 pt-3 mt-4">
        <button
          onClick={() => onDelete(template.id)}
          className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all"
          title="Остановить автоплатеж"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
