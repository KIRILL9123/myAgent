import { useState, type FormEvent } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { CheckCircle2, Plus, Shield, Sparkles, XCircle } from 'lucide-react';
import { createSkill, disableSkill, fetchSkills, type ProceduralSkill } from '../api/memory';
import { Button, Card, Dialog, EmptyState, ErrorState, LoadingState } from './ui';

const statusLabel: Record<ProceduralSkill['status'], string> = { draft: 'На подтверждении', approved: 'Активен', disabled: 'Отключён' };

export default function SkillsPanel() {
  const client = useQueryClient();
  const [editorOpen, setEditorOpen] = useState(false);
  const skills = useQuery({ queryKey: ['memory', 'skills'], queryFn: () => fetchSkills('all') });
  const disable = useMutation({ mutationFn: disableSkill, onSuccess: () => client.invalidateQueries({ queryKey: ['memory', 'skills'] }) });
  const invalidate = () => { client.invalidateQueries({ queryKey: ['memory', 'skills'] }); setEditorOpen(false); };

  if (skills.isLoading) return <LoadingState label="Загружаю навыки…" />;
  if (skills.isError) return <ErrorState message={skills.error instanceof Error ? skills.error.message : 'Не удалось загрузить навыки'} onRetry={() => skills.refetch()} />;
  const items = skills.data?.skills ?? [];

  return <div className="mx-auto max-w-6xl space-y-5">
    <Card className="border-fuchsia-500/20 bg-gradient-to-br from-fuchsia-500/10 to-zinc-900/40 p-5 sm:p-6">
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div><div className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-fuchsia-300" /><h2 className="text-lg font-bold">Навыки агента</h2></div><p className="mt-2 max-w-2xl text-sm text-zinc-400">Одобренные рабочие сценарии. Они не являются фактами о вас и не могут обходить подтверждения действий.</p></div>
        <Button tone="primary" onClick={() => setEditorOpen(true)}><Plus className="h-4 w-4" />Новый навык</Button>
      </div>
    </Card>
    {!items.length ? <EmptyState title="Навыков пока нет" description="Создайте первый сценарий — он появится в Центре подтверждений." /> : <div className="grid gap-4 md:grid-cols-2">{items.map(skill => <SkillCard key={skill.id} skill={skill} onDisable={() => disable.mutate(skill.id)} disabling={disable.isPending && disable.variables === skill.id} />)}</div>}
    {editorOpen && <SkillDialog onClose={() => setEditorOpen(false)} onSaved={invalidate} />}
  </div>;
}

function SkillCard({ skill, onDisable, disabling }: { skill: ProceduralSkill; onDisable: () => void; disabling: boolean }) {
  const tone = skill.status === 'approved' ? 'text-emerald-300 bg-emerald-500/10 border-emerald-500/20' : skill.status === 'draft' ? 'text-amber-300 bg-amber-500/10 border-amber-500/20' : 'text-zinc-500 bg-zinc-500/10 border-zinc-500/20';
  return <Card className="flex flex-col gap-4 p-5"><div className="flex items-start justify-between gap-3"><div className="min-w-0"><h3 className="text-sm font-semibold text-zinc-100">{skill.name}</h3><p className="mt-2 text-xs leading-relaxed text-zinc-400">{skill.description}</p></div><span className={`shrink-0 rounded-lg border px-2 py-1 text-[10px] font-semibold ${tone}`}>{statusLabel[skill.status]}</span></div><div className="flex flex-wrap gap-1">{skill.triggers.map(trigger => <span key={trigger} className="rounded bg-fuchsia-500/10 px-2 py-1 text-[10px] text-fuchsia-200">{trigger}</span>)}</div><div className="flex items-center gap-2 text-[11px] text-zinc-600"><Shield className="h-3.5 w-3.5" />{skill.source === 'builtin' ? 'Встроенный' : 'Пользовательский'} · использован {skill.use_count} раз</div>{skill.status === 'draft' && <p className="text-xs text-amber-300">Подтвердите навык в разделе «Подтверждения».</p>}{skill.status === 'approved' && skill.source !== 'builtin' && <Button tone="danger" onClick={onDisable} loading={disabling}><XCircle className="h-3.5 w-3.5" />Отключить</Button>}</Card>;
}

function SkillDialog({ onClose, onSaved }: { onClose: () => void; onSaved: () => void }) {
  const [name, setName] = useState(''); const [description, setDescription] = useState(''); const [triggers, setTriggers] = useState(''); const [steps, setSteps] = useState('');
  const mutation = useMutation({ mutationFn: () => createSkill({ name, description, category: 'general', triggers: triggers.split(',').map(item => item.trim()).filter(Boolean), steps: steps.split('\n').map(item => item.trim()).filter(Boolean) }), onSuccess: onSaved });
  return <Dialog title="Новый навык агента" description="После сохранения навык попадёт в Центр подтверждений и не будет активен до вашего одобрения." onClose={onClose}><form onSubmit={(event: FormEvent) => { event.preventDefault(); mutation.mutate(); }} className="space-y-4"><label className="block text-xs text-zinc-400">Название<input required value={name} onChange={event => setName(event.target.value)} className="input mt-1.5" placeholder="Например, research_trip" /></label><label className="block text-xs text-zinc-400">Описание<input value={description} onChange={event => setDescription(event.target.value)} className="input mt-1.5" /></label><label className="block text-xs text-zinc-400">Триггеры через запятую<input required value={triggers} onChange={event => setTriggers(event.target.value)} className="input mt-1.5" placeholder="поездка, travel, маршрут" /></label><label className="block text-xs text-zinc-400">Шаги — по одному на строку<textarea required rows={5} value={steps} onChange={event => setSteps(event.target.value)} className="input mt-1.5 resize-none" /></label>{mutation.isError && <p className="text-xs text-rose-300">{mutation.error instanceof Error ? mutation.error.message : 'Не удалось создать навык'}</p>}<div className="flex justify-end gap-2"><Button type="button" onClick={onClose}>Отмена</Button><Button type="submit" tone="primary" loading={mutation.isPending}><CheckCircle2 className="h-4 w-4" />Создать на подтверждение</Button></div></form></Dialog>;
}
