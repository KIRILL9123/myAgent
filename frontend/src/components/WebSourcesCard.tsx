import { ExternalLink, Globe2 } from 'lucide-react';
import type { WebSource } from '../api/chat';

export default function WebSourcesCard({ sources }: { sources: WebSource[] }) {
  if (!sources.length) return null;

  return (
    <section className="mt-4 overflow-hidden rounded-2xl border border-emerald-300/15 bg-emerald-950/20">
      <div className="flex items-center gap-2 border-b border-white/10 px-4 py-3 text-xs font-semibold uppercase tracking-[0.14em] text-emerald-200/75">
        <Globe2 className="h-4 w-4" />
        Источники
      </div>
      <div className="divide-y divide-white/5">
        {sources.map((source, index) => (
          <a
            key={`${source.url}-${index}`}
            href={source.url}
            target="_blank"
            rel="noreferrer"
            className="group block px-4 py-3 transition hover:bg-white/5"
          >
            <div className="flex items-start justify-between gap-3">
              <span className="line-clamp-2 text-sm font-medium text-zinc-200 group-hover:text-emerald-200">
                {source.title || source.url}
              </span>
              <ExternalLink className="mt-0.5 h-4 w-4 shrink-0 text-zinc-500 group-hover:text-emerald-300" />
            </div>
            <div className="mt-1 truncate text-[11px] text-emerald-300/60">{source.url}</div>
            {source.snippet && <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-zinc-500">{source.snippet}</p>}
          </a>
        ))}
      </div>
    </section>
  );
}
