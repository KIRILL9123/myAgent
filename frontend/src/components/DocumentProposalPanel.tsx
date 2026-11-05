import { useMemo, useState } from 'react';
import { CalendarPlus, CheckCircle2, FileSearch, ListChecks, Loader2, Sparkles } from 'lucide-react';
import { Link } from 'react-router-dom';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { createDocumentProposal, fetchDocumentProposals } from '../api/documents';
import type { DocumentActionType } from '../api/documents';
import { Button } from './ui';

const actionLabels: Record<DocumentActionType, string> = {
  commitment: 'Предложить задачу',
  calendar_event: 'Предложить событие',
};

const formatDate = (value: string) => new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });

export default function DocumentProposalPanel({ documentId }: { documentId: number }) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(false);
  const query = useQuery({
    queryKey: ['document-proposals', documentId],
    queryFn: () => fetchDocumentProposals(documentId),
    enabled: open,
    staleTime: 60_000,
  });
  const mutation = useMutation({
    mutationFn: ({ candidateId, actionType }: { candidateId: string; actionType: DocumentActionType }) => createDocumentProposal(documentId, candidateId, actionType),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['document-proposals', documentId] });
      queryClient.invalidateQueries({ queryKey: ['action-center'] });
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
    },
  });

  const pendingByCandidate = useMemo(() => {
    const result = new Map<string, Set<DocumentActionType>>();
    (query.data?.proposals || []).forEach(proposal => {
      if (!proposal.candidate_id) return;
      const actions = result.get(proposal.candidate_id) || new Set<DocumentActionType>();
      actions.add(proposal.action_type);
      result.set(proposal.candidate_id, actions);
    });
    return result;
  }, [query.data?.proposals]);

  return <div className="rounded-xl border border-zinc-800/80 bg-zinc-950/30 p-3">
    <div className="flex items-center justify-between gap-2">
      <div className="flex min-w-0 items-center gap-2 text-[11px] font-semibold text-zinc-400"><Sparkles className="h-3.5 w-3.5 text-amber-300" />Сроки и обязательства</div>
      <Button type="button" className="min-h-8 px-2.5 py-1 text-[11px]" onClick={() => setOpen(value => !value)}>
        <FileSearch className="h-3.5 w-3.5" />{open ? 'Скрыть' : 'Проверить'}
      </Button>
    </div>
    {open && <div className="mt-3 border-t border-zinc-800 pt-3">
      {query.isLoading ? <p className="flex items-center gap-2 text-[11px] text-zinc-600"><Loader2 className="h-3.5 w-3.5 animate-spin" />Проверяю текст документа…</p> : query.isError ? <p className="text-[11px] text-rose-300">Не удалось проверить документ. Попробуйте ещё раз.</p> : query.data?.candidates.length === 0 ? <p className="text-[11px] text-zinc-600">Явных обязательств с датами не найдено. Документ не изменён.</p> : <div className="space-y-3">
        {query.data?.candidates.map(candidate => {
          const proposed = pendingByCandidate.get(candidate.candidate_id) || new Set<DocumentActionType>();
          return <div key={candidate.candidate_id} className="rounded-lg border border-zinc-800 bg-zinc-900/60 p-3">
            <div className="flex items-start gap-2"><ListChecks className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-300" /><div className="min-w-0"><p className="text-xs font-semibold text-zinc-200">{candidate.title}</p><p className="mt-1 text-[11px] text-zinc-500">Срок: {formatDate(candidate.deadline_at)}</p><p className="mt-2 text-[11px] leading-relaxed text-zinc-400">{candidate.evidence}</p></div></div>
            <div className="mt-3 flex flex-wrap gap-2 border-t border-zinc-800 pt-2">
              {(['commitment', 'calendar_event'] as DocumentActionType[]).map(actionType => proposed.has(actionType) ? <span key={actionType} className="inline-flex items-center gap-1.5 rounded-lg border border-emerald-500/20 bg-emerald-500/10 px-2.5 py-1.5 text-[11px] text-emerald-300"><CheckCircle2 className="h-3.5 w-3.5" />В Центре действий</span> : <Button key={actionType} type="button" className="min-h-8 px-2.5 py-1 text-[11px]" onClick={() => mutation.mutate({ candidateId: candidate.candidate_id, actionType })} loading={mutation.isPending && mutation.variables?.candidateId === candidate.candidate_id && mutation.variables.actionType === actionType}><>{actionType === 'commitment' ? <ListChecks className="h-3.5 w-3.5" /> : <CalendarPlus className="h-3.5 w-3.5" />}{actionLabels[actionType]}</></Button>)}
            </div>
          </div>;
        })}
        <p className="text-[11px] text-zinc-600">Сначала появится предложение. Задача или событие создастся только после подтверждения в <Link to="/notifications" className="text-purple-300 hover:text-purple-200">Центре действий</Link>.</p>
      </div>}
      {mutation.isError && <p className="mt-2 text-[11px] text-rose-300">Не удалось создать предложение. Попробуйте ещё раз.</p>}
    </div>}
  </div>;
}
