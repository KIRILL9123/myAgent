import { Repeat, Tag, Trash2 } from 'lucide-react';
import type { RecurringTemplate } from '../../types';

interface RecurringTemplateCardProps {
  template: RecurringTemplate;
  formatCurrency: (value: number, currency?: string) => string;
  onDelete: (id: number) => void;
}

const WEEKDAYS = ['пн', 'вт', 'ср', 'чт', 'пт', 'сб', 'вс'];

function scheduleLabel(template: RecurringTemplate): string {
  if (template.frequency === 'weekly') {
    return `Каждую неделю, ${WEEKDAYS[template.day_of_week ?? 0]}`;
  }
  if (template.frequency === 'yearly') {
    return `Ежегодно, ${template.day_of_month}.${String(template.month_of_year ?? 1).padStart(2, '0')}`;
  }
  return `Каждое ${template.day_of_month ?? '—'}-е число месяца`;
}

export default function RecurringTemplateCard({ template, formatCurrency, onDelete }: RecurringTemplateCardProps) {
  return (
    <div className="bg-zinc-900/20 border border-zinc-900 rounded-2xl p-4.5 flex flex-col justify-between hover:border-zinc-800/60 transition-all shadow-sm">
      <div className="flex flex-col gap-2.5">
        <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
          <span>{scheduleLabel(template)}</span>
          <span className={`uppercase font-bold px-2 py-0.5 rounded-lg border flex items-center gap-0.5 ${template.active ? 'text-emerald-555 bg-emerald-500/5 border-emerald-500/10' : 'text-zinc-500 bg-zinc-800/40 border-zinc-700'}`}>
            <Repeat className="h-2.5 w-2.5" />
            {template.active ? 'Авто' : 'Остановлен'}
          </span>
        </div>

        <div className="flex justify-between items-center gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <div className="p-2 rounded-xl bg-zinc-800/40 text-zinc-450 shrink-0">
              <Tag className="h-4 w-4" />
            </div>
            <span className="text-xs font-semibold text-zinc-350 truncate pr-1">{template.category}</span>
          </div>
          <span className="text-xs font-bold text-rose-400 font-mono shrink-0">-{formatCurrency(template.amount, template.currency)}</span>
        </div>

        {template.description && (
          <p className="text-xs text-zinc-550 line-clamp-1 italic font-sans pl-8">{template.description}</p>
        )}
      </div>

      <div className="flex justify-end border-t border-zinc-800/30 pt-3 mt-4">
        <button
          onClick={() => onDelete(template.id)}
          disabled={!template.active}
          className="p-1.5 rounded-lg text-zinc-500 hover:text-red-400 hover:bg-red-500/10 transition-all disabled:cursor-not-allowed disabled:opacity-40"
          title="Остановить автоплатёж"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
