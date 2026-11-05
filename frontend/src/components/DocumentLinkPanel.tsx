import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, Link2, ListChecks, Loader2, Plus, Receipt, Unlink, X } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  createDocumentLink,
  deleteDocumentLink,
  fetchDocumentLinkTargets,
  fetchDocumentLinks,
} from '../api/documents';
import type { DocumentLinkType } from '../api/documents';
import { Button } from './ui';

const typeLabels: Record<DocumentLinkType, string> = {
  commitment: 'Задача',
  calendar_event: 'Календарь',
  subscription: 'Подписка',
};

const typeIcons: Record<DocumentLinkType, typeof Link2> = {
  commitment: ListChecks,
  calendar_event: CalendarDays,
  subscription: Receipt,
};

const types: DocumentLinkType[] = ['commitment', 'calendar_event', 'subscription'];

export default function DocumentLinkPanel({ documentId }: { documentId: number }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const [targetType, setTargetType] = useState<DocumentLinkType>('commitment');
  const [targetId, setTargetId] = useState('');

  const linksQuery = useQuery({
    queryKey: ['document-links', documentId],
    queryFn: () => fetchDocumentLinks(documentId),
    staleTime: 60_000,
  });
  const targetsQuery = useQuery({
    queryKey: ['document-link-targets'],
    queryFn: fetchDocumentLinkTargets,
    staleTime: 60_000,
  });

  const targets = useMemo(() => targetsQuery.data?.targets ?? [], [targetsQuery.data]);
  const filteredTargets = useMemo(
    () => targets.filter(target => target.target_type === targetType),
    [targetType, targets],
  );
  const selectedTarget = filteredTargets.find(target => target.id === targetId);

  useEffect(() => {
    if (targetId && !filteredTargets.some(target => target.id === targetId)) setTargetId('');
  }, [filteredTargets, targetId]);

  const addMutation = useMutation({
    mutationFn: () => {
      if (!selectedTarget) throw new Error('Выберите цель связи');
      return createDocumentLink(documentId, {
        target_type: targetType,
        target_id: selectedTarget.id,
        target_label: selectedTarget.label,
      });
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-links', documentId] });
      setTargetId('');
      setOpen(false);
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (linkId: number) => deleteDocumentLink(documentId, linkId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['document-links', documentId] }),
  });

  const links = linksQuery.data?.links ?? [];

  return (
    <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/30 p-3">
      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-2 text-[11px] font-semibold text-zinc-400">
          <Link2 className="h-3.5 w-3.5 text-purple-300" />
          Контекст документа
        </div>
        <Button type="button" className="min-h-8 px-2.5 py-1 text-[11px]" onClick={() => setOpen(value => !value)}>
          {open ? <X className="h-3.5 w-3.5" /> : <Plus className="h-3.5 w-3.5" />}
          {open ? 'Закрыть' : 'Связать'}
        </Button>
      </div>

      {linksQuery.isLoading ? (
        <p className="mt-3 flex items-center gap-2 text-[11px] text-zinc-600"><Loader2 className="h-3.5 w-3.5 animate-spin" />Загружаю связи…</p>
      ) : links.length > 0 ? (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {links.map(link => {
            const Icon = typeIcons[link.target_type];
            return <span key={link.id} className="inline-flex max-w-full items-center gap-1.5 rounded-lg border border-zinc-800 bg-zinc-900/70 px-2 py-1 text-[11px] text-zinc-300">
              <Icon className="h-3 w-3 shrink-0 text-zinc-500" />
              <Link to={link.target_path} className="truncate hover:text-zinc-100" title={link.target_label}>{link.target_label}</Link>
              <button type="button" className="ml-0.5 text-zinc-600 transition-colors hover:text-rose-300" onClick={() => deleteMutation.mutate(link.id)} disabled={deleteMutation.isPending} aria-label={`Удалить связь: ${link.target_label}`}>
                <Unlink className="h-3 w-3" />
              </button>
            </span>;
          })}
        </div>
      ) : <p className="mt-2 text-[11px] text-zinc-600">Задачи, события и подписки можно прикрепить как контекст.</p>}

      {open && <div className="mt-3 space-y-2 border-t border-zinc-800 pt-3">
        <div className="grid gap-2 sm:grid-cols-[10rem_minmax(0,1fr)_auto]">
          <select className="input h-9 text-xs" value={targetType} onChange={event => setTargetType(event.target.value as DocumentLinkType)}>
            {types.map(type => <option key={type} value={type}>{typeLabels[type]}</option>)}
          </select>
          <select className="input h-9 min-w-0 text-xs" value={targetId} onChange={event => setTargetId(event.target.value)} disabled={targetsQuery.isLoading || filteredTargets.length === 0}>
            <option value="">{targetsQuery.isLoading ? 'Загружаю варианты…' : filteredTargets.length ? 'Выберите цель…' : 'Нет доступных целей'}</option>
            {filteredTargets.map(target => <option key={target.id} value={target.id}>{target.label}{target.detail ? ` · ${target.detail}` : ''}</option>)}
          </select>
          <Button type="button" tone="primary" className="h-9 px-3 text-xs" onClick={() => addMutation.mutate()} loading={addMutation.isPending} disabled={!selectedTarget}>Добавить</Button>
        </div>
        {addMutation.isError && <p className="text-[11px] text-rose-300">{addMutation.error instanceof Error ? addMutation.error.message : 'Не удалось создать связь'}</p>}
        {targetsQuery.isError && <p className="text-[11px] text-amber-300">Не удалось загрузить список целей. Связи можно повторить позже.</p>}
      </div>}
    </div>
  );
}
