import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react';
import { Loader2, X } from 'lucide-react';

type Tone = 'neutral' | 'primary' | 'success' | 'danger';

const toneClasses: Record<Tone, string> = {
  neutral: 'border-zinc-700 bg-zinc-900 text-zinc-300 hover:border-zinc-600 hover:text-zinc-100',
  primary: 'border-purple-500/30 bg-purple-600 text-white hover:bg-purple-500',
  success: 'border-emerald-500/30 bg-emerald-600 text-white hover:bg-emerald-500',
  danger: 'border-rose-500/30 bg-rose-500/10 text-rose-200 hover:bg-rose-500/20',
};

export function Button({ tone = 'neutral', loading = false, children, className = '', disabled, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone; loading?: boolean }) {
  return <button {...props} disabled={disabled || loading} className={`inline-flex min-h-10 items-center justify-center gap-2 rounded-xl border px-3.5 py-2 text-xs font-semibold transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-purple-400/70 disabled:cursor-not-allowed disabled:opacity-50 ${toneClasses[tone]} ${className}`}>
    {loading && <Loader2 className="h-4 w-4 animate-spin" />}{children}
  </button>;
}

export function Card({ children, className = '', ...props }: HTMLAttributes<HTMLElement>) {
  return <section {...props} className={`rounded-2xl border border-zinc-800/90 bg-zinc-900/45 shadow-[0_12px_36px_rgba(0,0,0,0.16)] ${className}`}>{children}</section>;
}

export function PageHeader({ icon, title, description, action }: { icon: ReactNode; title: string; description?: string; action?: ReactNode }) {
  return <header className="flex shrink-0 items-center justify-between gap-4 border-b border-zinc-900 px-4 py-4 sm:px-6">
    <div className="flex min-w-0 items-center gap-3"><span className="shrink-0 text-purple-300">{icon}</span><div className="min-w-0"><h1 className="truncate text-lg font-bold tracking-tight text-zinc-100 sm:text-xl">{title}</h1>{description && <p className="mt-1 truncate text-xs text-zinc-500">{description}</p>}</div></div>{action}
  </header>;
}

export function LoadingState({ label = 'Загрузка…' }: { label?: string }) {
  return <div className="flex min-h-40 items-center justify-center gap-3 rounded-2xl border border-dashed border-zinc-800 text-xs text-zinc-500"><Loader2 className="h-5 w-5 animate-spin text-purple-400" />{label}</div>;
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return <div className="rounded-2xl border border-dashed border-zinc-800 p-10 text-center"><p className="text-sm font-semibold text-zinc-300">{title}</p>{description && <p className="mt-2 text-xs text-zinc-600">{description}</p>}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 text-xs text-rose-200"><span>{message}</span>{onRetry && <Button onClick={onRetry}>Повторить</Button>}</div>;
}

export function Dialog({ title, description, children, onClose }: { title: string; description?: string; children: ReactNode; onClose: () => void }) {
  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm" role="presentation" onMouseDown={(event) => { if (event.currentTarget === event.target) onClose(); }}>
    <div className="w-full max-w-md rounded-2xl border border-zinc-700 bg-zinc-900 p-5 shadow-2xl" role="dialog" aria-modal="true" aria-labelledby="dialog-title"><div className="flex items-start justify-between gap-4"><div><h2 id="dialog-title" className="text-base font-semibold text-zinc-100">{title}</h2>{description && <p className="mt-1 text-xs leading-relaxed text-zinc-500">{description}</p>}</div><button onClick={onClose} aria-label="Закрыть" className="rounded-lg p-1.5 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200"><X className="h-4 w-4" /></button></div><div className="mt-5">{children}</div></div>
  </div>;
}
