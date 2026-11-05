import type { ButtonHTMLAttributes, HTMLAttributes, ReactNode } from 'react';
import { Loader2, X } from 'lucide-react';
import * as DialogPrimitive from '@radix-ui/react-dialog';

type Tone = 'neutral' | 'primary' | 'success' | 'danger';

const toneClasses: Record<Tone, string> = {
  neutral: 'ui-button-neutral',
  primary: 'ui-button-primary',
  success: 'ui-button-success',
  danger: 'ui-button-danger',
};

export function Button({ tone = 'neutral', loading = false, children, className = '', disabled, ...props }: ButtonHTMLAttributes<HTMLButtonElement> & { tone?: Tone; loading?: boolean }) {
  return (
    <button {...props} disabled={disabled || loading} className={`ui-button ${toneClasses[tone]} ${className}`}>
      {loading && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
      {children}
    </button>
  );
}

export function Card({ children, className = '', ...props }: HTMLAttributes<HTMLElement>) {
  return <section {...props} className={`surface-card ${className}`}>{children}</section>;
}

export function PageHeader({ icon, title, description, action }: { icon: ReactNode; title: string; description?: string; action?: ReactNode }) {
  return (
    <header className="page-header">
      <div className="page-header-title">
        <span className="page-header-icon" aria-hidden="true">{icon}</span>
        <div className="min-w-0"><h1>{title}</h1>{description && <p>{description}</p>}</div>
      </div>
      {action && <div className="page-header-actions">{action}</div>}
    </header>
  );
}

export function LoadingState({ label = 'Загрузка…' }: { label?: string }) {
  return <div className="state-box"><Loader2 className="h-5 w-5 animate-spin text-[var(--app-accent)]" aria-hidden="true" />{label}</div>;
}

export function EmptyState({ title, description }: { title: string; description?: string }) {
  return <div className="state-box state-box-empty"><p>{title}</p>{description && <span>{description}</span>}</div>;
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return <div className="state-box state-box-error"><span>{message}</span>{onRetry && <Button onClick={onRetry}>Повторить</Button>}</div>;
}

export function Dialog({ title, description, children, onClose }: { title: string; description?: string; children: ReactNode; onClose: () => void }) {
  return (
    <DialogPrimitive.Root open onOpenChange={open => { if (!open) onClose(); }}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="dialog-backdrop" />
        <DialogPrimitive.Content className="dialog-panel">
          <div className="dialog-heading">
            <div>
              <DialogPrimitive.Title className="dialog-title">{title}</DialogPrimitive.Title>
              {description && <DialogPrimitive.Description className="dialog-description">{description}</DialogPrimitive.Description>}
            </div>
            <DialogPrimitive.Close asChild>
              <button type="button" aria-label="Закрыть" className="dialog-close"><X className="h-4 w-4" /></button>
            </DialogPrimitive.Close>
          </div>
          <div className="mt-5">{children}</div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
