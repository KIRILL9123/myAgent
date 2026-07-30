import { AlertTriangle, Calendar, CornerUpLeft, Loader2, User } from 'lucide-react';
import type { EmailMessage, MailAccount } from '../../types';

interface EmailCardProps {
  email: EmailMessage;
  account: MailAccount;
  index: number;
  analyzing: boolean;
  formatEmailDate: (value: string) => string;
  cleanPreviewText: (value: string) => string;
  onAnalyze: (email: EmailMessage, index: number) => void;
  onReply: (email: EmailMessage) => void;
}

export default function EmailCard({
  email,
  account,
  index,
  analyzing,
  formatEmailDate,
  cleanPreviewText,
  onAnalyze,
  onReply,
}: EmailCardProps) {
  return (
    <div className="bg-zinc-900/40 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all flex flex-col justify-between group shadow-md hover:shadow-lg">
      <div className="flex flex-col gap-3.5">
        <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3" />
            <span>{formatEmailDate(email.date)}</span>
          </div>
          <span className="uppercase text-blue-500/80 font-bold bg-blue-500/5 px-2 py-0.5 rounded-lg border border-blue-500/10">
            {account}
          </span>
        </div>

        <div className="flex items-center gap-2.5 min-w-0">
          <div className="p-2 rounded-xl bg-zinc-800/60 text-zinc-400 border border-zinc-800 shrink-0">
            <User className="h-4 w-4" />
          </div>
          <div className="min-w-0">
            <span className="block text-xs font-semibold text-zinc-300 truncate">
              {cleanPreviewText(email.from)}
            </span>
          </div>
        </div>

        <h2 className="text-sm font-semibold text-zinc-200 tracking-wide line-clamp-2 mt-1">
          {cleanPreviewText(email.subject)}
        </h2>

        {email.preview && (
          <p className="text-xs text-zinc-550 leading-relaxed font-sans line-clamp-3 mt-1.5 min-h-[3rem]">
            {cleanPreviewText(email.preview)}
          </p>
        )}
      </div>

      <div className="flex justify-end gap-2 border-t border-zinc-800/40 pt-4 mt-5">
        <button
          onClick={() => onAnalyze(email, index)}
          disabled={analyzing}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-amber-400 hover:text-amber-300 hover:bg-amber-500/10 transition-all border border-transparent hover:border-amber-500/25 cursor-pointer"
        >
          {analyzing ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <AlertTriangle className="h-3.5 w-3.5" />}
          Обязательства
        </button>
        <button
          onClick={() => onReply(email)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-zinc-450 hover:text-blue-400 hover:bg-blue-500/10 transition-all border border-transparent hover:border-blue-500/25 cursor-pointer"
        >
          <CornerUpLeft className="h-3.5 w-3.5" />
          Ответить
        </button>
      </div>
    </div>
  );
}
