import { useEffect, useState } from 'react';
import { Activity, CheckCircle2, RefreshCw, XCircle } from 'lucide-react';
import { fetchSystemStatus } from '../api/system';
import type { SystemStatus } from '../api/system';

export default function SystemStatusWidget() {
  const [status, setStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);

  const load = async () => {
    setLoading(true); setError(false);
    try { setStatus(await fetchSystemStatus()); }
    catch { setError(true); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const healthy = status?.overall === 'ok';
  return (
    <section className="mx-auto mb-6 max-w-5xl rounded-2xl border border-zinc-900 bg-zinc-900/30 p-4 shadow-md sm:p-5">
      <div className="flex items-center justify-between gap-3">
        <div className="flex min-w-0 items-center gap-3"><div className={`rounded-xl p-2.5 ${healthy ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-300'}`}><Activity className="h-5 w-5" /></div><div className="min-w-0"><h2 className="text-sm font-semibold text-zinc-200">Состояние системы</h2><p className="truncate text-xs text-zinc-500">{loading ? 'Проверяю сервисы…' : error ? 'Не удалось получить диагностику' : healthy ? 'Backend и модель доступны' : 'Требует внимания'}</p></div></div>
        <button onClick={load} className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-800 hover:text-zinc-200" aria-label="Обновить состояние"><RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} /></button>
      </div>
      {!loading && !error && status && <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4"><StatusItem label="Backend" ok={status.backend.status === 'ok'} detail="API" /><StatusItem label={status.llm.provider === 'openai_compatible' ? 'Bonsai' : 'Ollama'} ok={status.llm.status === 'ok'} detail={status.llm.latency_ms == null ? status.llm.detail || 'offline' : `${Math.round(status.llm.latency_ms)} ms`} /><StatusItem label="Порт модели" ok={status.ports[0]?.reachable === true} detail={status.ports[0]?.port ? String(status.ports[0].port) : '—'} /><StatusItem label="Последняя проверка" ok detail={new Date(status.generated_at).toLocaleTimeString('ru-RU')} /></div>}
    </section>
  );
}

function StatusItem({ label, ok, detail }: { label: string; ok: boolean; detail: string }) {
  return <div className="flex items-center gap-2 rounded-xl border border-zinc-800 bg-zinc-950/40 px-3 py-2"><span className={ok ? 'text-emerald-400' : 'text-rose-400'}>{ok ? <CheckCircle2 className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}</span><div className="min-w-0"><div className="truncate text-[10px] font-semibold text-zinc-400">{label}</div><div className="truncate text-[10px] text-zinc-600">{detail}</div></div></div>;
}
