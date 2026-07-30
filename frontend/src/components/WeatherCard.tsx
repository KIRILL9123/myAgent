import { Cloud, CloudRain, Droplets, Sun, Umbrella, Wind } from 'lucide-react';
import type { ReactNode } from 'react';
import type { WeatherData } from '../api/chat';

function weatherIcon(code: number) {
  if (code === 0 || code === 1) return <Sun className="h-12 w-12 text-amber-200" />;
  if (code >= 51 && code <= 82) return <CloudRain className="h-12 w-12 text-sky-200" />;
  if (code >= 95) return <CloudRain className="h-12 w-12 text-violet-200" />;
  return <Cloud className="h-12 w-12 text-zinc-200" />;
}

function shortDate(value: string): string {
  return new Date(`${value}T12:00:00`).toLocaleDateString('ru-RU', { weekday: 'short' }).replace('.', '');
}

function temp(value: number | null | undefined): string {
  return value == null ? '—' : `${Math.round(value)}°`;
}

export default function WeatherCard({ weather }: { weather: WeatherData }) {
  const current = weather.current;
  return (
    <section className="w-full max-w-xl overflow-hidden rounded-3xl border border-sky-300/20 bg-gradient-to-br from-sky-950 via-indigo-950 to-zinc-950 shadow-2xl shadow-sky-950/30">
      <div className="relative p-5 sm:p-6"><div className="absolute -right-10 -top-12 h-40 w-40 rounded-full bg-sky-400/10 blur-3xl" /><div className="relative flex items-start justify-between gap-4"><div><div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-[0.18em] text-sky-200/70"><span className="h-2 w-2 rounded-full bg-emerald-300 shadow-[0_0_10px_#6ee7b7]" />Сейчас</div><h3 className="mt-2 text-2xl font-bold text-white">{weather.location.name}</h3><p className="mt-1 text-sm text-sky-100/70">{weather.location.country} · {current.condition}</p></div><div className="pt-1">{weatherIcon(current.weather_code)}</div></div><div className="relative mt-5 flex items-end gap-3"><span className="text-6xl font-extralight tracking-tighter text-white">{temp(current.temperature_c)}</span><span className="mb-2 text-sm text-sky-100/70">Ощущается {temp(current.apparent_temperature_c)}</span></div><div className="relative mt-5 grid grid-cols-3 gap-2"><WeatherMetric icon={<Wind className="h-4 w-4" />} label="Ветер" value={`${Math.round(current.wind_speed_kmh)} км/ч`} /><WeatherMetric icon={<Droplets className="h-4 w-4" />} label="Осадки" value={`${current.precipitation_mm ?? 0} мм`} /><WeatherMetric icon={<Umbrella className="h-4 w-4" />} label="Обновлено" value={current.observed_at?.split('T')[1]?.slice(0, 5) || 'сейчас'} /></div></div>
      <div className="border-t border-white/10 bg-black/10 px-5 py-4 sm:px-6"><div className="mb-3 flex items-center justify-between"><span className="text-xs font-semibold uppercase tracking-[0.16em] text-sky-100/60">Прогноз</span><span className="text-[10px] text-sky-100/40">{weather.source.provider}</span></div><div className="grid grid-cols-5 gap-1">{weather.daily.slice(0, 5).map((day, index) => <div key={day.date} className={`rounded-2xl px-1 py-2 text-center ${index === 0 ? 'bg-white/10' : ''}`}><div className="text-[10px] font-semibold capitalize text-sky-100/60">{index === 0 ? 'Сегодня' : shortDate(day.date)}</div><div className="my-2 flex justify-center">{weatherIcon(day.weather_code)}</div><div className="text-xs font-semibold text-white">{temp(day.temperature_max_c)}</div><div className="text-[10px] text-sky-100/50">{temp(day.temperature_min_c)}</div><div className="mt-2 text-[9px] text-sky-200/50">{day.precipitation_probability_percent ?? 0}%</div></div>)}</div></div>
    </section>
  );
}

function WeatherMetric({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return <div className="rounded-2xl border border-white/10 bg-white/5 px-2 py-2.5"><div className="flex items-center gap-1.5 text-sky-100/50">{icon}<span className="text-[10px]">{label}</span></div><div className="mt-1 text-xs font-semibold text-white/90">{value}</div></div>;
}
