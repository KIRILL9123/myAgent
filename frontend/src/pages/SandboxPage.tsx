import { useEffect, useMemo, useState } from 'react';
import { Code2, FileCode2, FolderOpen, GitCompare, Play, RefreshCw, Save, ShieldCheck, Trash2 } from 'lucide-react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui';
import {
  captureSandboxBaseline,
  deleteSandboxFile,
  fetchSandbox,
  fetchSandboxDiff,
  fetchSandboxFile,
  runSandboxCheck,
  requestSandboxApply,
  writeSandboxFile,
} from '../api/sandbox';

function getWorkspaceId(): string {
  const key = 'home-agent-sandbox-session';
  const current = window.localStorage.getItem(key);
  if (current) return current;
  const created = `web-${crypto.randomUUID()}`;
  window.localStorage.setItem(key, created);
  return created;
}

export default function SandboxPage() {
  const queryClient = useQueryClient();
  const [sessionId] = useState(getWorkspaceId);
  const [selectedPath, setSelectedPath] = useState('main.py');
  const [content, setContent] = useState('print("Hello from Mira sandbox")\n');
  const [check, setCheck] = useState<'python' | 'pytest' | 'node' | 'compile_python'>('python');
  const [output, setOutput] = useState('');
  const [status, setStatus] = useState<string | null>(null);
  const snapshot = useQuery({ queryKey: ['sandbox', sessionId], queryFn: () => fetchSandbox(sessionId), staleTime: 10_000 });
  const diff = useQuery({ queryKey: ['sandbox-diff', sessionId], queryFn: () => fetchSandboxDiff(sessionId), staleTime: 5_000 });
  const files = useMemo(() => snapshot.data?.files.filter(item => item.type === 'file') ?? [], [snapshot.data]);
  const runtime = snapshot.data?.runtime;
  const lifecycle = snapshot.data?.lifecycle;
  const lifecycleLabel = lifecycle?.state === 'draft_changed'
    ? 'Есть изменения после checkpoint'
    : lifecycle?.state === 'checkpointed'
      ? 'Workspace зафиксирован'
      : lifecycle?.state === 'runtime_unavailable'
        ? 'Runner недоступен'
        : 'Пустой workspace';
  const runtimeNotice = !runtime
    ? 'Песочница загружает runtime…'
    : runtime.ready && runtime.configured_runtime === 'docker'
      ? 'Docker runner активен: сеть отключена, ресурсы ограничены.'
      : runtime.message;

  const write = useMutation({
    mutationFn: () => writeSandboxFile(sessionId, { path: selectedPath, content, overwrite: true }),
    onSuccess: () => {
      setStatus('Файл сохранён в песочнице');
      queryClient.invalidateQueries({ queryKey: ['sandbox', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sandbox-diff', sessionId] });
    },
  });
  const execute = useMutation({
    mutationFn: () => runSandboxCheck(sessionId, { check, path: selectedPath, timeout_seconds: 30 }),
    onSuccess: result => {
      setOutput([result.stdout, result.stderr].filter(Boolean).join('\n') || result.message || `Код завершения: ${result.return_code ?? '—'}`);
      setStatus(result.status === 'success' ? 'Проверка завершена успешно' : `Проверка завершена со статусом: ${result.status}`);
    },
  });
  const baseline = useMutation({
    mutationFn: () => captureSandboxBaseline(sessionId),
    onSuccess: result => {
      setStatus(`Точка сравнения сохранена: ${result.file_count} файлов`);
      queryClient.invalidateQueries({ queryKey: ['sandbox-diff', sessionId] });
    },
  });
  const remove = useMutation({
    mutationFn: () => deleteSandboxFile(sessionId, selectedPath),
    onSuccess: () => {
      setStatus('Файл удалён из песочницы');
      queryClient.invalidateQueries({ queryKey: ['sandbox', sessionId] });
      queryClient.invalidateQueries({ queryKey: ['sandbox-diff', sessionId] });
    },
  });
  const applyRequest = useMutation({
    mutationFn: () => requestSandboxApply(sessionId),
    onSuccess: result => {
      setStatus('Запрос отправлен в Центр подтверждений');
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      setOutput(result.message);
    },
  });

  useEffect(() => {
    let active = true;
    if (!files.some(file => file.path === selectedPath)) return () => { active = false; };
    fetchSandboxFile(sessionId, selectedPath).then(file => { if (active) setContent(file.content); }).catch(() => undefined);
    return () => { active = false; };
  }, [sessionId, selectedPath, files]);

  const error = snapshot.error || diff.error || write.error || execute.error || baseline.error || remove.error || applyRequest.error;
  const summary = diff.data?.summary;
  return <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
    <PageHeader
      icon={<Code2 className="h-5 w-5 text-cyan-300" />}
      title="Песочница"
      description="Черновики кода и проверки вне основного проекта"
      action={<Button onClick={() => { snapshot.refetch(); diff.refetch(); }} loading={snapshot.isFetching || diff.isFetching} aria-label="Обновить"><RefreshCw className="h-4 w-4" /></Button>}
    />
    <main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
      <div className={`flex items-start gap-3 rounded-2xl border p-4 text-xs leading-relaxed ${runtime?.ready ? 'border-emerald-500/20 bg-emerald-500/5 text-zinc-400' : 'border-amber-500/20 bg-amber-500/5 text-zinc-400'}`}>
        <ShieldCheck className={`mt-0.5 h-4 w-4 shrink-0 ${runtime?.ready ? 'text-emerald-300' : 'text-amber-300'}`} />
        <span><strong className="font-semibold text-zinc-300">{runtime?.ready ? 'Изолированный runner' : 'Runner недоступен'}</strong><br />{runtimeNotice}</span>
      </div>
      {lifecycle && <div className="flex flex-wrap items-center justify-between gap-2 rounded-xl border border-zinc-800 bg-zinc-900/40 px-4 py-3 text-xs text-zinc-400"><span><strong className="font-semibold text-zinc-200">Состояние workspace:</strong> {lifecycleLabel}</span><span>Checkpoint: {new Date(lifecycle.baseline_at).toLocaleString('ru-RU')}</span></div>}
      {error && <ErrorState message={error instanceof Error ? error.message : 'Операция песочницы не выполнена'} />}
      {snapshot.isLoading ? <LoadingState label="Загружаю рабочее пространство…" /> : <>
        <div className="grid grid-cols-1 gap-5 xl:grid-cols-[240px_minmax(0,1fr)]">
          <Card className="p-4">
            <div className="mb-3 flex items-center justify-between"><h2 className="text-sm font-semibold">Файлы</h2><span className="text-[10px] text-zinc-600">{snapshot.data?.total_bytes ?? 0} B</span></div>
            {files.length === 0 ? <EmptyState title="Файлов пока нет" description="Сохраните первый черновик справа." /> : <div className="space-y-1">{files.map(file => <button key={file.path} onClick={() => setSelectedPath(file.path)} className={`flex w-full items-center gap-2 rounded-lg px-3 py-2 text-left text-xs ${selectedPath === file.path ? 'bg-purple-500/15 text-purple-200' : 'text-zinc-400 hover:bg-zinc-800/60 hover:text-zinc-200'}`}><FileCode2 className="h-4 w-4 shrink-0" />{file.path}</button>)}</div>}
            <div className="mt-4 border-t border-zinc-800 pt-3 text-[10px] leading-relaxed text-zinc-600"><FolderOpen className="mb-1 h-4 w-4" />Workspace: {sessionId}</div>
          </Card>
          <Card className="flex min-h-[560px] flex-col p-4">
            <div className="flex flex-wrap items-center gap-2">
              <input value={selectedPath} onChange={event => setSelectedPath(event.target.value)} className="input min-w-0 flex-1 font-mono text-xs" placeholder="main.py" />
              <select value={check} onChange={event => setCheck(event.target.value as typeof check)} className="input w-36 text-xs"><option value="python">Python</option><option value="compile_python">Compile</option><option value="pytest">Pytest</option><option value="node">Node</option></select>
              <Button onClick={() => write.mutate()} tone="primary" loading={write.isPending}><Save className="h-4 w-4" />Сохранить</Button>
              <Button onClick={() => execute.mutate()} loading={execute.isPending}><Play className="h-4 w-4" />Проверить</Button>
              <Button onClick={() => remove.mutate()} tone="danger" loading={remove.isPending} disabled={!files.some(file => file.path === selectedPath)} aria-label="Удалить файл"><Trash2 className="h-4 w-4" /></Button>
            </div>
            <textarea value={content} onChange={event => setContent(event.target.value)} spellCheck={false} className="mt-4 min-h-[320px] flex-1 resize-y rounded-xl border border-zinc-800 bg-zinc-950 p-4 font-mono text-xs leading-relaxed text-zinc-200 outline-none focus:border-purple-500/60" />
            {status && <p className="mt-3 text-xs text-emerald-300">{status}</p>}
            <div className="mt-4"><p className="mb-2 text-[10px] font-bold uppercase tracking-widest text-zinc-600">Вывод проверки</p><pre className="min-h-24 overflow-x-auto whitespace-pre-wrap rounded-xl border border-zinc-800 bg-black/30 p-3 font-mono text-xs text-zinc-400">{output || 'Здесь появится stdout/stderr после проверки.'}</pre></div>
          </Card>
        </div>
        <Card className="p-4">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <div className="flex items-center gap-2"><GitCompare className="h-4 w-4 text-purple-300" /><div><h2 className="text-sm font-semibold">Изменения</h2><p className="text-xs text-zinc-500">Сравнение с сохранённой точкой, без доступа к основному проекту</p></div></div>
            <div className="flex flex-wrap gap-2"><Button onClick={() => baseline.mutate()} loading={baseline.isPending}>Зафиксировать точку</Button><Button onClick={() => applyRequest.mutate()} tone="primary" loading={applyRequest.isPending} disabled={!summary?.changed_files}>Запросить применение</Button></div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2 text-xs"><span className="rounded-full bg-emerald-500/10 px-3 py-1 text-emerald-300">Добавлено: {summary?.added ?? 0}</span><span className="rounded-full bg-amber-500/10 px-3 py-1 text-amber-300">Изменено: {summary?.modified ?? 0}</span><span className="rounded-full bg-rose-500/10 px-3 py-1 text-rose-300">Удалено: {summary?.removed ?? 0}</span></div>
          {diff.isLoading ? <p className="mt-4 text-xs text-zinc-500">Считаю diff…</p> : diff.data?.files.length ? <div className="mt-4 space-y-2">{diff.data.files.map(file => <details key={file.path} className="rounded-xl border border-zinc-800 bg-black/20"><summary className="cursor-pointer list-none px-3 py-2 text-xs text-zinc-300"><span className="mr-2 inline-block w-16 text-[10px] uppercase tracking-widest text-zinc-600">{file.status}</span>{file.path}<span className="float-right text-zinc-600">+{file.additions} / -{file.deletions}</span></summary><pre className="overflow-x-auto border-t border-zinc-800 p-3 font-mono text-[11px] leading-relaxed text-zinc-400">{file.diff || 'Нет текстового diff'}</pre></details>)}</div> : <p className="mt-4 text-xs text-zinc-500">Изменений относительно точки сравнения нет.</p>}
        </Card>
      </>}
    </main>
  </div>;
}
