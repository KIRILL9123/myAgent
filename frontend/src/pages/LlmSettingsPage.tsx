import { useEffect, useState } from 'react';
import { Check, Cloud, Cpu, Loader2, RefreshCw, ShieldCheck, XCircle } from 'lucide-react';
import {
  checkLlmProvider,
  fetchLlmStatus,
  setLlmModels,
  setLlmProvider,
  type LlmCheckResult,
  type LlmProfile,
  type LlmProviderId,
  type LlmStatus,
} from '../api/llm';

export default function LlmSettingsPage() {
  const [status, setStatus] = useState<LlmStatus | null>(null);
  const [check, setCheck] = useState<LlmCheckResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [switching, setSwitching] = useState<LlmProviderId | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      setStatus(await fetchLlmStatus());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Не удалось получить настройки LLM');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const switchProvider = async (provider: LlmProviderId) => {
    setSwitching(provider);
    setError(null);
    setCheck(null);
    try {
      setStatus(await setLlmProvider(provider));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Не удалось переключить провайдера');
    } finally {
      setSwitching(null);
    }
  };

  const verify = async (provider: LlmProviderId) => {
    setCheck(null);
    setError(null);
    try {
      setCheck(await checkLlmProvider(provider));
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Проверка провайдера не выполнена');
    }
  };

  return (
    <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
      <header className="flex shrink-0 items-center justify-between border-b border-zinc-900 px-4 py-3 sm:px-6 sm:py-4">
        <div className="flex min-w-0 items-center gap-3">
          <Cpu className="h-5 w-5 shrink-0 text-purple-300" />
          <div>
            <h1 className="text-lg font-bold sm:text-xl">LLM-провайдер</h1>
            <p className="mt-1 text-xs text-zinc-500">Переключение без перезапуска</p>
          </div>
        </div>
        <button
          onClick={() => void load()}
          className="rounded-lg p-2 text-zinc-500 hover:bg-zinc-900 hover:text-zinc-200"
          aria-label="Обновить настройки"
        >
          <RefreshCw className={`h-4 w-4 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </header>
      <main className="flex-1 space-y-5 overflow-y-auto p-4 sm:p-6">
        <div className="flex items-start gap-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-xs leading-relaxed text-zinc-400">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-emerald-300" />
          <span>
            Ключ DeepSeek хранится только в переменной окружения сервера. Экран не показывает и не сохраняет секреты.
            Для облачного провайдера включено обезличивание чувствительных данных.
          </span>
        </div>
        {loading && !status ? (
          <div className="flex h-48 items-center justify-center">
            <Loader2 className="h-7 w-7 animate-spin text-purple-300" />
          </div>
        ) : error && !status ? (
          <ErrorBox message={error} />
        ) : status ? (
          <>
            <section className="grid gap-4 md:grid-cols-2">
              {status.profiles.map((profile) => (
                <ProviderCard
                  key={profile.id}
                  profile={profile}
                  switching={switching === profile.id}
                  onSelect={() => void switchProvider(profile.id)}
                  onCheck={() => void verify(profile.id)}
                  onSave={async (models) => {
                    setError(null);
                    try {
                      setStatus(await setLlmModels(profile.id, models));
                    } catch (err: unknown) {
                      setError(err instanceof Error ? err.message : 'Не удалось сохранить модели');
                    }
                  }}
                />
              ))}
            </section>
            <section className="rounded-2xl border border-zinc-800 bg-zinc-900/40 p-4 sm:p-5">
              <h2 className="mb-3 text-sm font-semibold">Текущая конфигурация</h2>
              <div className="grid gap-2 text-xs text-zinc-400 sm:grid-cols-3">
                <div>
                  Провайдер: <strong className="text-zinc-200">{status.active_provider}</strong>
                </div>
                <div>
                  Основная модель: <strong className="text-zinc-200">{status.active_model}</strong>
                </div>
                <div>
                  Fallback:{' '}
                  <strong className="text-zinc-200">{status.fallback_enabled ? 'включён' : 'выключен'}</strong>
                </div>
              </div>
            </section>
            {check && (
              <div
                className={`rounded-2xl border p-4 text-sm ${check.status === 'ok' ? 'border-emerald-500/20 bg-emerald-500/5 text-emerald-200' : 'border-amber-500/20 bg-amber-500/5 text-amber-200'}`}
              >
                {check.status === 'ok' ? (
                  <Check className="mr-2 inline h-4 w-4" />
                ) : (
                  <XCircle className="mr-2 inline h-4 w-4" />
                )}
                {check.detail}
                {check.latency_ms != null ? ` · ${check.latency_ms} ms` : ''}
              </div>
            )}
            {error && <ErrorBox message={error} />}
          </>
        ) : null}
      </main>
    </div>
  );
}

function ProviderCard({
  profile,
  switching,
  onSelect,
  onCheck,
  onSave,
}: {
  profile: LlmProfile;
  switching: boolean;
  onSelect: () => void;
  onCheck: () => void;
  onSave: (models: Partial<LlmProfile['models']>) => Promise<void>;
}) {
  const isLocal = profile.id === 'local';
  const [models, setModels] = useState(profile.models);
  const { main, extractor, classifier } = profile.models;
  useEffect(() => {
    setModels({ main, extractor, classifier });
  }, [main, extractor, classifier]);
  return (
    <article
      className={`rounded-2xl border p-4 sm:p-5 ${profile.active ? 'border-purple-400/50 bg-purple-500/5' : 'border-zinc-800 bg-zinc-900/40'}`}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          {isLocal ? <Cpu className="h-5 w-5 text-cyan-300" /> : <Cloud className="h-5 w-5 text-sky-300" />}
          <div>
            <h2 className="font-semibold">{profile.label}</h2>
            <p className="mt-1 text-xs text-zinc-500">{profile.endpoint}</p>
          </div>
        </div>
        {profile.active && (
          <span className="rounded-full bg-purple-400/15 px-2 py-1 text-[10px] font-semibold text-purple-200">
            активен
          </span>
        )}
      </div>
      <div className="mt-4 space-y-2 text-xs text-zinc-400">
        {(['main', 'extractor', 'classifier'] as const).map((role) => (
          <label key={role} className="flex items-center gap-2">
            <span className="w-20">{role}:</span>
            <input
              value={models[role]}
              onChange={(event) => setModels((current) => ({ ...current, [role]: event.target.value }))}
              className="min-w-0 flex-1 rounded-lg border border-zinc-700 bg-zinc-950 px-2 py-1 font-mono text-zinc-300 outline-none focus:border-purple-400"
            />
          </label>
        ))}
      </div>
      {!profile.configured && (
        <p className="mt-4 text-xs text-amber-300">Не настроен: добавьте DEEPSEEK_API_KEY на сервере.</p>
      )}
      <div className="mt-5 flex gap-2">
        <button
          disabled={!profile.configured || profile.active || switching}
          onClick={onSelect}
          className="flex-1 rounded-xl bg-purple-600 px-3 py-2 text-xs font-semibold text-white disabled:cursor-not-allowed disabled:opacity-40"
        >
          {switching ? 'Переключение…' : profile.active ? 'Используется' : 'Сделать активным'}
        </button>
        <button
          onClick={() => void onSave(models)}
          className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800"
        >
          Сохранить модели
        </button>
        <button
          onClick={onCheck}
          className="rounded-xl border border-zinc-700 px-3 py-2 text-xs text-zinc-300 hover:bg-zinc-800"
        >
          Проверить
        </button>
      </div>
    </article>
  );
}

function ErrorBox({ message }: { message: string }) {
  return (
    <div className="rounded-2xl border border-rose-500/20 bg-rose-500/5 p-4 text-sm text-rose-200">
      <XCircle className="mr-2 inline h-4 w-4" />
      {message}
    </div>
  );
}
