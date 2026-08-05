import { useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react';
import { AlertCircle, Check, CheckCircle2, Clock3, Loader2, Plus, RefreshCw, ShieldCheck, Target, X } from 'lucide-react';
import { approveCommitment, cancelCommitment, completeCommitment, fetchCommitments } from '../api/commitments';
import type { Commitment, CommitmentStatus } from '../api/commitments';
import { createGoal, createProject, fetchGoals, fetchProjects, linkTaskToProject } from '../api/planning';
import type { Goal, Project } from '../api/planning';

type View = 'tasks' | 'goals' | 'projects';
const STATUS_LABELS: Record<CommitmentStatus, string> = { PROPOSED: 'На подтверждении', ACTIVE: 'Активные', COMPLETED: 'Выполненные', CANCELLED: 'Отменённые', EXPIRED: 'Просроченные' };
const formatDate = (value: string | null) => value ? new Date(value).toLocaleString('ru-RU', { dateStyle: 'medium', timeStyle: 'short' }) : 'Без срока';
const formatDay = (value: string | null) => value ? new Date(`${value}T00:00:00`).toLocaleDateString('ru-RU', { dateStyle: 'medium' }) : 'Без даты';

export default function CommitmentsPage() {
  const [view, setView] = useState<View>('tasks');
  const [tasks, setTasks] = useState<Commitment[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyId, setBusyId] = useState<string | null>(null);
  const [dialog, setDialog] = useState<'goal' | 'project' | null>(null);
  const [goalTitle, setGoalTitle] = useState('');
  const [goalDate, setGoalDate] = useState('');
  const [projectTitle, setProjectTitle] = useState('');
  const [projectGoal, setProjectGoal] = useState('');
  const [projectDate, setProjectDate] = useState('');

  const load = async () => {
    setLoading(true); setError(null);
    try {
      const [taskList, goalList, projectList] = await Promise.all([fetchCommitments(true), fetchGoals(), fetchProjects()]);
      setTasks(taskList); setGoals(goalList.goals); setProjects(projectList.projects);
    } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось загрузить планирование'); }
    finally { setLoading(false); }
  };
  useEffect(() => { void load(); }, []);

  const proposed = useMemo(() => tasks.filter(item => item.status === 'PROPOSED'), [tasks]);
  const active = useMemo(() => tasks.filter(item => item.status === 'ACTIVE'), [tasks]);
  const history = useMemo(() => tasks.filter(item => ['COMPLETED', 'CANCELLED', 'EXPIRED'].includes(item.status)), [tasks]);
  const runAction = async (id: string, action: 'approve' | 'complete' | 'cancel') => {
    setBusyId(id); setError(null);
    try { if (action === 'approve') await approveCommitment(id); if (action === 'complete') await completeCommitment(id); if (action === 'cancel') await cancelCommitment(id); await load(); }
    catch (err) { setError(err instanceof Error ? err.message : 'Не удалось изменить задачу'); }
    finally { setBusyId(null); }
  };
  const saveGoal = async (event: FormEvent) => { event.preventDefault(); try { await createGoal({ title: goalTitle, description: null, target_date: goalDate || null }); setDialog(null); setGoalTitle(''); setGoalDate(''); await load(); } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось создать цель'); } };
  const saveProject = async (event: FormEvent) => { event.preventDefault(); try { await createProject({ title: projectTitle, goal_id: projectGoal || null, target_date: projectDate || null }); setDialog(null); setProjectTitle(''); setProjectGoal(''); setProjectDate(''); await load(); } catch (err) { setError(err instanceof Error ? err.message : 'Не удалось создать проект'); } };

  return <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
    <header className="flex shrink-0 items-center justify-between border-b border-zinc-900 px-4 py-3 sm:px-6 sm:py-4"><div className="flex min-w-0 items-center gap-3"><CheckCircle2 className="h-5 w-5 shrink-0 text-emerald-400" /><div><h1 className="text-lg font-bold sm:text-xl">Планирование</h1><p className="mt-1 text-xs text-zinc-500">Цели, проекты и задачи в одной иерархии</p></div></div><button onClick={() => void load()} aria-label="Обновить планирование" className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200"><RefreshCw className="h-4 w-4" /></button></header>
    <nav className="flex shrink-0 gap-1 overflow-x-auto border-b border-zinc-900 px-4 py-2 sm:px-6">{([['tasks', 'Задачи'], ['goals', 'Цели'], ['projects', 'Проекты']] as Array<[View, string]>).map(([key, label]) => <button key={key} onClick={() => setView(key)} className={`rounded-lg px-3 py-2 text-xs font-semibold ${view === key ? 'bg-emerald-600 text-white' : 'text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200'}`}>{label}</button>)}<span className="flex-1" />{view === 'goals' && <button onClick={() => setDialog('goal')} className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold hover:bg-emerald-500"><Plus className="h-3.5 w-3.5" />Цель</button>}{view === 'projects' && <button onClick={() => setDialog('project')} className="flex items-center gap-1 rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold hover:bg-emerald-500"><Plus className="h-3.5 w-3.5" />Проект</button>}</nav>
    <main className="flex-1 space-y-6 overflow-y-auto p-4 sm:space-y-8 sm:p-6">{error && <div className="flex items-center gap-2 rounded-xl border border-red-500/20 bg-red-500/10 p-4 text-xs text-red-200"><AlertCircle className="h-4 w-4" />{error}</div>}{loading ? <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-emerald-400" /></div> : view === 'tasks' ? <TasksView proposed={proposed} active={active} history={history} busyId={busyId} runAction={runAction} /> : view === 'goals' ? <GoalsView goals={goals} /> : <ProjectsView projects={projects} tasks={active} onLinked={load} />}</main>
    {dialog === 'goal' && <Dialog title="Новая цель" onClose={() => setDialog(null)}><form onSubmit={saveGoal} className="space-y-4"><label className="block text-xs text-zinc-400">Название<input required value={goalTitle} onChange={event => setGoalTitle(event.target.value)} className="input mt-1.5" /></label><label className="block text-xs text-zinc-400">Целевая дата<input type="date" value={goalDate} onChange={event => setGoalDate(event.target.value)} className="input mt-1.5" /></label><FormActions onClose={() => setDialog(null)} /></form></Dialog>}
    {dialog === 'project' && <Dialog title="Новый проект" onClose={() => setDialog(null)}><form onSubmit={saveProject} className="space-y-4"><label className="block text-xs text-zinc-400">Название<input required value={projectTitle} onChange={event => setProjectTitle(event.target.value)} className="input mt-1.5" /></label><label className="block text-xs text-zinc-400">Цель<select value={projectGoal} onChange={event => setProjectGoal(event.target.value)} className="input mt-1.5"><option value="">Без цели</option>{goals.filter(goal => goal.status !== 'ARCHIVED').map(goal => <option key={goal.id} value={goal.id}>{goal.title}</option>)}</select></label><label className="block text-xs text-zinc-400">Целевая дата<input type="date" value={projectDate} onChange={event => setProjectDate(event.target.value)} className="input mt-1.5" /></label><FormActions onClose={() => setDialog(null)} /></form></Dialog>}
  </div>;
}

function TasksView({ proposed, active, history, busyId, runAction }: { proposed: Commitment[]; active: Commitment[]; history: Commitment[]; busyId: string | null; runAction: (id: string, action: 'approve' | 'complete' | 'cancel') => void }) {
  const renderCard = (item: Commitment) => <article key={item.id} className="flex flex-col gap-4 rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5 shadow-lg"><div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-semibold leading-relaxed">{item.title}</h2>{item.description && <p className="mt-2 text-xs leading-relaxed text-zinc-500">{item.description}</p>}</div><span className="shrink-0 rounded-lg border border-zinc-700 bg-zinc-800/60 px-2 py-1 text-[10px] font-bold text-zinc-300">{STATUS_LABELS[item.status]}</span></div><div className="grid grid-cols-2 gap-3 text-[11px] text-zinc-500"><div className="flex items-center gap-2"><Clock3 className="h-3.5 w-3.5" />{formatDate(item.deadline_at)}</div><div>Источник: {item.source_type}</div>{item.project_id && <div className="col-span-2 text-emerald-300">Проект связан</div>}</div><div className="flex gap-2 border-t border-zinc-800 pt-3">{item.status === 'PROPOSED' && <button onClick={() => runAction(item.id, 'approve')} disabled={busyId === item.id} className="flex items-center gap-1.5 rounded-lg bg-emerald-600/80 px-3 py-2 text-[11px] font-semibold hover:bg-emerald-500"><ShieldCheck className="h-3.5 w-3.5" />Подтвердить</button>}{item.status === 'ACTIVE' && <button onClick={() => runAction(item.id, 'complete')} disabled={busyId === item.id} className="flex items-center gap-1.5 rounded-lg bg-blue-600/80 px-3 py-2 text-[11px] font-semibold hover:bg-blue-500"><Check className="h-3.5 w-3.5" />Выполнено</button>}{(item.status === 'PROPOSED' || item.status === 'ACTIVE') && <button onClick={() => runAction(item.id, 'cancel')} disabled={busyId === item.id} className="flex items-center gap-1.5 rounded-lg border border-zinc-700 px-3 py-2 text-[11px] font-semibold text-zinc-400 hover:border-red-500/50 hover:text-red-300"><X className="h-3.5 w-3.5" />Отменить</button>}{busyId === item.id && <Loader2 className="h-4 w-4 animate-spin self-center text-zinc-500" />}</div></article>;
  const section = (title: string, items: Commitment[], color: string, empty: string) => <section><h2 className={`mb-3 text-xs font-bold uppercase tracking-widest ${color}`}>{title} · {items.length}</h2>{items.length ? <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">{items.map(renderCard)}</div> : <p className="rounded-xl border border-dashed border-zinc-800 p-6 text-sm text-zinc-600">{empty}</p>}</section>;
  return <>{section('Требуют подтверждения', proposed, 'text-amber-300', 'Новых предложений нет.')}{section('Активные', active, 'text-blue-300', 'Активных задач нет.')}{history.length > 0 && section('История', history, 'text-zinc-500', '')}</>;
}

function GoalsView({ goals }: { goals: Goal[] }) { if (!goals.length) return <Empty title="Целей пока нет" description="Добавьте цель вручную или попросите Mira сделать это в чате." />; return <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{goals.map(goal => <article key={goal.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5"><Target className="h-5 w-5 text-emerald-400" /><h2 className="mt-4 text-sm font-semibold">{goal.title}</h2><p className="mt-2 text-xs text-zinc-500">{goal.status === 'ACTIVE' ? 'Активная цель' : goal.status}</p><p className="mt-4 text-xs text-zinc-400">{formatDay(goal.target_date)}</p></article>)}</div>; }

function ProjectsView({ projects, tasks, onLinked }: { projects: Project[]; tasks: Commitment[]; onLinked: () => Promise<void> }) { const [selected, setSelected] = useState<Record<string, string>>({}); if (!projects.length) return <Empty title="Проектов пока нет" description="Проект можно создать здесь или попросить Mira в чате." />; return <div className="grid gap-4 md:grid-cols-2">{projects.map(project => <article key={project.id} className="rounded-2xl border border-zinc-800 bg-zinc-900/50 p-5"><div className="flex items-start justify-between gap-3"><div><h2 className="text-sm font-semibold">{project.title}</h2><p className="mt-2 text-xs text-zinc-500">{project.goal_id ? 'Связан с целью' : 'Без цели'} · {project.status}</p></div><span className="text-xs text-zinc-500">{formatDay(project.target_date)}</span></div><div className="mt-5 border-t border-zinc-800 pt-4"><label className="text-[11px] text-zinc-500">Привязать активную задачу</label><div className="mt-2 flex gap-2"><select value={selected[project.id] || ''} onChange={event => setSelected(prev => ({ ...prev, [project.id]: event.target.value }))} className="input min-w-0 flex-1"><option value="">Выберите задачу</option>{tasks.filter(task => !task.project_id).map(task => <option key={task.id} value={task.id}>{task.title}</option>)}</select><button disabled={!selected[project.id]} onClick={async () => { await linkTaskToProject(project.id, selected[project.id]); setSelected(prev => ({ ...prev, [project.id]: '' })); await onLinked(); }} className="rounded-lg border border-zinc-700 px-3 text-xs text-zinc-300 disabled:opacity-40">Связать</button></div></div></article>)}</div>; }

function Empty({ title, description }: { title: string; description: string }) { return <div className="mx-auto max-w-xl rounded-2xl border border-dashed border-zinc-800 p-10 text-center"><h2 className="text-sm font-semibold">{title}</h2><p className="mt-2 text-xs text-zinc-500">{description}</p></div>; }
function Dialog({ title, onClose, children }: { title: string; onClose: () => void; children: ReactNode }) { return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4"><section className="w-full max-w-md rounded-2xl border border-zinc-700 bg-zinc-900 p-5 shadow-2xl"><div className="flex items-center justify-between"><h2 className="font-semibold">{title}</h2><button onClick={onClose} className="text-zinc-500 hover:text-zinc-100"><X className="h-4 w-4" /></button></div><div className="mt-5">{children}</div></section></div>; }
function FormActions({ onClose }: { onClose: () => void }) { return <div className="flex justify-end gap-2"><button type="button" onClick={onClose} className="rounded-lg border border-zinc-700 px-3 py-2 text-xs text-zinc-400">Отмена</button><button type="submit" className="rounded-lg bg-emerald-600 px-3 py-2 text-xs font-semibold hover:bg-emerald-500">Сохранить</button></div>; }
