import { useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { Activity, Cpu, HardDrive, Loader2, MemoryStick, RefreshCw, Server, XCircle } from 'lucide-react';
import { fetchSystemStatus } from '../api/system';
import type { HostDiagnostics } from '../api/system';

function formatBytes(value: number | null): string {
  if (value == null) return '—';
  const units = ['Б', 'КБ', 'МБ', 'ГБ', 'ТБ'];
  let amount = value; let index = 0;
  while (amount >= 1024 && index < units.length - 1) { amount /= 1024; index += 1; }
  return `${amount.toFixed(index > 1 ? 1 : 0)} ${units[index]}`;
}

function percent(value: number | null): string { return value == null ? '—' : `${value.toFixed(1)}%`; }

export default function SystemPage() {
  const [metrics, setMetrics] = useState<HostDiagnostics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setMetrics((await fetchSystemStatus()).host_metrics); }
    catch (err: any) { setError(err.message || 'Не удалось получить диагностику компьютера'); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex shrink-0 items-center justify-between border-b border-zinc-900 px-4 py-3 sm:px-6 sm:py-4"><div className="flex min-w-0 items-center gap-3"><Activity className="h-5 w-5 shrink-0 text-sky-400" /><div className="min-w-0"><h1 className="truncate text-lg font-bold sm:text-xl">Система</h1><p className="mt-1 truncate text-xs text-zinc-500">Read-only диагностика компьютера</p></div></div><button onClick={load} className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200" aria-label="Обновить диагностику"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button></header>
      <main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
        <div className="rounded-2xl border border-sky-500/20 bg-sky-500/5 p-4 text-xs leading-relaxed text-zinc-400">Этот экран только читает состояние хоста. Процессы не запускаются, не останавливаются и не изменяются.</div>
        {loading ? <div className="flex h-48 items-center justify-center"><Loader2 className="h-7 w-7 animate-spin text-sky-400" /></div> : error || !metrics ? <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-6 text-sm text-rose-200"><XCircle className="mb-2 h-5 w-5" />{error || 'Нет данных'}</div> : <DiagnosticsContent metrics={metrics} />}
      </main>
    </div>
  );
}

function DiagnosticsContent({ metrics }: { metrics: HostDiagnostics }) {
  return <>
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-3"><MetricCard icon={<Cpu className="h-5 w-5" />} title="CPU" value={percent(metrics.cpu.percent)} detail={`${metrics.cpu.cores} cores`} /><MetricCard icon={<MemoryStick className="h-5 w-5" />} title="RAM" value={percent(metrics.memory.used_percent)} detail={`${formatBytes(metrics.memory.available_bytes)} свободно`} /><MetricCard icon={<Server className="h-5 w-5" />} title="Процессы" value={metrics.process_count == null ? '—' : String(metrics.process_count)} detail={`сборка ${metrics.collection_latency_ms.toFixed(0)} ms`} /></div>
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 sm:p-5"><div className="mb-4 flex items-center gap-2"><HardDrive className="h-4 w-4 text-amber-300" /><h2 className="text-sm font-semibold">Диски</h2></div><div className="space-y-4">{metrics.disks.map(disk => <div key={disk.name}><div className="mb-1 flex justify-between text-xs"><span className="text-zinc-300">{disk.name}</span><span className="text-zinc-500">{percent(disk.used_percent)} занято · {formatBytes(disk.free_bytes)} свободно</span></div><div className="h-2 overflow-hidden rounded-full bg-zinc-800"><div className={`h-full rounded-full ${disk.used_percent != null && disk.used_percent >= 90 ? 'bg-rose-500' : disk.used_percent != null && disk.used_percent >= 75 ? 'bg-amber-400' : 'bg-emerald-500'}`} style={{ width: `${Math.min(100, disk.used_percent || 0)}%` }} /></div></div>)}{metrics.disks.length === 0 && <p className="text-xs text-zinc-600">Диски не обнаружены</p>}</div></section>
    <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 sm:p-5"><h2 className="mb-4 text-sm font-semibold">Топ процессов по памяти</h2><div className="overflow-x-auto"><table className="w-full min-w-[520px] text-left text-xs"><thead className="text-zinc-600"><tr><th className="pb-2 font-medium">Процесс</th><th className="pb-2 font-medium">PID</th><th className="pb-2 font-medium">CPU time</th><th className="pb-2 text-right font-medium">RAM</th></tr></thead><tbody className="divide-y divide-zinc-800/70">{metrics.processes.map(process => <tr key={`${process.name}-${process.pid}`}><td className="py-2 text-zinc-300">{process.name}</td><td className="py-2 font-mono text-zinc-600">{process.pid}</td><td className="py-2 text-zinc-500">{process.cpu_seconds == null ? '—' : `${process.cpu_seconds.toFixed(1)} s`}</td><td className="py-2 text-right text-zinc-500">{formatBytes(process.memory_bytes)}</td></tr>)}</tbody></table></div></section>
  </>;
}

function MetricCard({ icon, title, value, detail }: { icon: ReactNode; title: string; value: string; detail: string }) {
  return <div className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-5"><div className="mb-4 flex items-center gap-2 text-sky-300">{icon}<span className="text-xs font-semibold uppercase tracking-widest text-zinc-500">{title}</span></div><div className="text-2xl font-bold text-zinc-100">{value}</div><div className="mt-1 text-xs text-zinc-600">{detail}</div></div>;
}
