import { useEffect, useRef, useState } from 'react';
import { Archive, FileStack, Search, Upload } from 'lucide-react';
import { archiveDocument, fetchDocuments, searchDocuments, uploadDocument } from '../api/documents';
import type { DocumentItem, DocumentSearchResult } from '../api/documents';
import { Button, Card, EmptyState, ErrorState, LoadingState, PageHeader } from '../components/ui';

const formatSize = (bytes: number) => bytes < 1024 * 1024 ? `${Math.max(1, Math.round(bytes / 1024))} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`;
const formatDate = (value: string) => new Date(value).toLocaleDateString('ru-RU', { day: 'numeric', month: 'short', year: 'numeric' });

export default function DocumentsPage() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [results, setResults] = useState<DocumentSearchResult[]>([]);
  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  const load = async () => {
    setLoading(true); setError(null);
    try { setDocuments((await fetchDocuments()).documents); } catch (err: any) { setError(err.message || 'Не удалось загрузить документы'); } finally { setLoading(false); }
  };
  useEffect(() => { load(); }, []);

  const upload = async (file: File) => {
    setBusy(true); setError(null); setNotice(null);
    try { const item = await uploadDocument(file); await load(); setNotice(item.status === 'ready' ? `«${item.original_name}» добавлен в Vault.` : `Документ добавлен, но не обработан: ${item.error_message || 'неизвестная ошибка'}`); }
    catch (err: any) { setError(err.message || 'Не удалось загрузить документ'); }
    finally { setBusy(false); if (inputRef.current) inputRef.current.value = ''; }
  };

  const search = async () => {
    if (!query.trim()) { setResults([]); return; }
    setBusy(true); setError(null);
    try { setResults((await searchDocuments(query)).results); } catch (err: any) { setError(err.message || 'Не удалось выполнить поиск'); } finally { setBusy(false); }
  };

  const archive = async (id: number) => {
    setBusy(true); setError(null);
    try { await archiveDocument(id); await load(); } catch (err: any) { setError(err.message || 'Не удалось архивировать документ'); } finally { setBusy(false); }
  };

  return <div className="flex h-full w-full flex-col overflow-hidden bg-zinc-950 text-zinc-100">
    <PageHeader icon={<FileStack className="h-5 w-5" />} title="Документы" description="Локальное хранилище и поиск по вашим файлам" action={<><input ref={inputRef} type="file" accept=".txt,.md,.markdown,.csv,.json,.html,.htm,.pdf" className="hidden" onChange={event => { const file = event.target.files?.[0]; if (file) upload(file); }} /><Button tone="primary" onClick={() => inputRef.current?.click()} loading={busy}><Upload className="h-4 w-4" />Загрузить</Button></>} />
    <main className="min-h-0 flex-1 overflow-y-auto p-4 sm:p-6"><div className="mx-auto max-w-6xl space-y-5">
      {notice && <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-xs text-emerald-200">{notice}</div>}
      {error && <ErrorState message={error} onRetry={load} />}
      <Card className="p-4 sm:p-5"><div className="flex flex-col gap-3 sm:flex-row"><div className="relative min-w-0 flex-1"><Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-zinc-600" /><input value={query} onChange={event => setQuery(event.target.value)} onKeyDown={event => { if (event.key === 'Enter') search(); }} className="input pl-9" placeholder="Поиск по содержимому документов…" /></div><Button onClick={search} loading={busy}>Найти</Button></div>{results.length > 0 && <div className="mt-4 space-y-2 border-t border-zinc-800 pt-4"><p className="text-xs font-semibold text-zinc-400">Результаты поиска</p>{results.map(result => <div key={result.chunk_id} className="rounded-xl border border-zinc-800 bg-zinc-950/60 p-3"><p className="text-xs font-semibold text-purple-200">{result.document_name}</p><p className="mt-2 whitespace-pre-wrap text-xs leading-relaxed text-zinc-400">{result.content}</p></div>)}</div>}</Card>
      {loading ? <LoadingState label="Загружаю документы…" /> : documents.length === 0 ? <EmptyState title="Документов пока нет" description="Загрузите PDF, Markdown, TXT, CSV, JSON или HTML — агент сможет искать по их содержимому в чате." /> : <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">{documents.map(document => <Card key={document.id} className="flex flex-col gap-4 p-5"><div className="flex items-start justify-between gap-3"><div className="flex min-w-0 items-center gap-3"><div className="rounded-xl bg-purple-500/10 p-2 text-purple-300"><FileStack className="h-5 w-5" /></div><div className="min-w-0"><h2 className="truncate text-sm font-semibold">{document.original_name}</h2><p className="mt-1 text-[11px] text-zinc-600">{formatSize(document.size_bytes)} · {formatDate(document.created_at)}</p></div></div><span className={`rounded-lg border px-2 py-1 text-[10px] ${document.status === 'ready' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-rose-500/20 bg-rose-500/10 text-rose-300'}`}>{document.status === 'ready' ? 'Готов' : 'Ошибка'}</span></div><p className="text-xs text-zinc-500">Индексировано символов: {document.extracted_chars.toLocaleString('ru-RU')}</p><Button tone="danger" onClick={() => archive(document.id)} disabled={busy}><Archive className="h-3.5 w-3.5" />Убрать из поиска</Button></Card>)}</div>}
    </div></main>
  </div>;
}
