import { useState, useEffect } from 'react';
import { 
  Mail, 
  Search, 
  Send, 
  Loader2, 
  AlertCircle, 
  CornerUpLeft, 
  Eye, 
  ChevronLeft, 
  CheckCircle,
  Inbox,
  User,
  Calendar,
  AlertTriangle,
  X
} from 'lucide-react';
import { 
  fetchUnreadEmails, 
  searchEmails, 
  sendEmail
} from '../api/mail';
import type { EmailMessage } from '../api/mail';

interface MailFormState {
  to: string;
  subject: string;
  body: string;
}

export default function MailPage() {
  const [account, setAccount] = useState<'gmail' | 'ukrnet'>('gmail');
  const [emails, setEmails] = useState<EmailMessage[]>([]);
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [isSearching, setIsSearching] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Compose/Reply states
  const [isComposeOpen, setIsComposeOpen] = useState<boolean>(false);
  const [formState, setFormState] = useState<MailFormState>({
    to: '',
    subject: '',
    body: '',
  });

  // Preview / Send states
  const [isPreviewOpen, setIsPreviewOpen] = useState<boolean>(false);
  const [sending, setSending] = useState<boolean>(false);
  const [sendSuccess, setSendSuccess] = useState<boolean>(false);

  // Load emails
  const loadEmails = async (searchStr?: string) => {
    setLoading(true);
    setError(null);
    try {
      let data: EmailMessage[];
      if (searchStr && searchStr.trim()) {
        data = await searchEmails(searchStr.trim(), account);
        setIsSearching(true);
      } else {
        data = await fetchUnreadEmails(account);
        setIsSearching(false);
      }
      setEmails(data);
    } catch (err: any) {
      setError(err.message || 'Ошибка при загрузке почты');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadEmails();
  }, [account]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    loadEmails(searchQuery);
  };

  const handleClearSearch = () => {
    setSearchQuery('');
    loadEmails('');
  };

  const extractEmailAddress = (fromStr: string): string => {
    const match = fromStr.match(/<([^>]+)>/);
    return match ? match[1] : fromStr.trim();
  };

  const handleReplyClick = (emailItem: EmailMessage) => {
    const replyTo = extractEmailAddress(emailItem.from);
    const replySubject = emailItem.subject.toLowerCase().startsWith('re:') 
      ? emailItem.subject 
      : `Re: ${emailItem.subject}`;

    setFormState({
      to: replyTo,
      subject: replySubject,
      body: '',
    });
    setIsComposeOpen(true);
  };

  const handleOpenComposeNew = () => {
    setFormState({
      to: '',
      subject: '',
      body: '',
    });
    setIsComposeOpen(true);
  };

  const handlePreviewClick = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formState.to.trim() || !formState.subject.trim() || !formState.body.trim()) {
      return;
    }
    setIsPreviewOpen(true);
  };

  const handleRealSend = async () => {
    setSending(true);
    try {
      await sendEmail({
        to: formState.to,
        subject: formState.subject,
        body: formState.body,
        account: account
      });
      setSendSuccess(true);
      setTimeout(() => {
        setSendSuccess(false);
        setIsPreviewOpen(false);
        setIsComposeOpen(false);
        loadEmails();
      }, 2000);
    } catch (err: any) {
      alert(`Ошибка отправки письма: ${err.message}`);
    } finally {
      setSending(false);
    }
  };

  const cleanPreviewText = (text: string): string => {
    // Remove prompt injection guard tags from UI display
    return text
      .replace(/<untrusted_external_content>/g, '')
      .replace(/<\/untrusted_external_content>/g, '');
  };

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Top Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-3 w-3 animate-pulse rounded-full bg-blue-500 shadow-[0_0_8px_#3b82f6]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Почтовый Клиент
          </h1>
        </div>

        <div className="text-xs text-zinc-500 font-mono hidden md:block">
          Home Agent IMAP/SMTP
        </div>
      </header>

      {/* Main content body */}
      <main className="flex-1 overflow-y-auto w-full h-full flex flex-col">
        {/* Controls Bar */}
        <div className="flex flex-col md:flex-row gap-4 justify-between items-center px-6 py-5 bg-zinc-950/40 border-b border-zinc-900 shrink-0">
          {/* Account switcher and compose */}
          <div className="flex flex-wrap gap-3.5 items-center w-full md:w-auto">
            {/* Account select pills */}
            <div className="flex bg-zinc-900 border border-zinc-800/80 rounded-xl p-1 shrink-0">
              <button
                onClick={() => setAccount('gmail')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  account === 'gmail'
                    ? 'bg-blue-650 text-zinc-100 shadow-md shadow-blue-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Gmail
              </button>
              <button
                onClick={() => setAccount('ukrnet')}
                className={`px-4 py-2 rounded-lg text-xs font-semibold tracking-wide transition-all ${
                  account === 'ukrnet'
                    ? 'bg-blue-650 text-zinc-100 shadow-md shadow-blue-900/30'
                    : 'text-zinc-400 hover:text-zinc-200'
                }`}
              >
                Ukr.net
              </button>
            </div>

            <button
              onClick={handleOpenComposeNew}
              className="flex items-center justify-center gap-2 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-lg shadow-blue-950/20"
            >
              <Mail className="h-4 w-4" />
              Написать письмо
            </button>
          </div>

          {/* Search bar */}
          <form onSubmit={handleSearchSubmit} className="flex gap-2 w-full md:w-80 shrink-0">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-zinc-500" />
              <input
                type="text"
                placeholder="Поиск по теме..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full bg-zinc-900 border border-zinc-800 focus:border-blue-500 rounded-xl pl-9.5 pr-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all"
              />
            </div>
            <button
              type="submit"
              className="bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 hover:border-zinc-700 px-4 py-2.5 rounded-xl text-xs font-semibold text-zinc-300 transition-all shrink-0"
            >
              Найти
            </button>
            {isSearching && (
              <button
                type="button"
                onClick={handleClearSearch}
                className="text-xs font-medium text-zinc-550 hover:text-zinc-350 transition-colors shrink-0"
              >
                Сбросить
              </button>
            )}
          </form>
        </div>

        {/* Display Content Area */}
        <div className="flex-1 w-full p-6">
          {loading ? (
            <div className="w-full h-64 flex flex-col items-center justify-center gap-3">
              <Loader2 className="h-8 w-8 animate-spin text-blue-500" />
              <span className="text-zinc-500 text-xs font-medium">Подключение к IMAP-серверу...</span>
            </div>
          ) : error ? (
            <div className="bg-red-500/10 border border-red-500/20 text-red-200 text-xs px-5 py-4 rounded-xl flex items-center gap-3 max-w-xl mx-auto mt-6">
              <AlertCircle className="h-5 w-5 text-red-400 shrink-0" />
              <div className="flex-1">
                <span className="font-bold">Ошибка:</span> {error}
              </div>
              <button 
                onClick={() => loadEmails(searchQuery)}
                className="bg-red-950/40 hover:bg-red-900/40 text-red-300 font-semibold px-3 py-1.5 rounded-lg text-[10px] tracking-wide transition-all uppercase border border-red-500/20"
              >
                Повторить
              </button>
            </div>
          ) : emails.length === 0 ? (
            <div className="w-full max-w-md mx-auto h-64 flex flex-col items-center justify-center gap-4 text-center border border-zinc-900 border-dashed rounded-2xl bg-zinc-950/20 px-6 mt-6">
              <Inbox className="h-10 w-10 text-zinc-650" />
              <div>
                <h3 className="text-sm font-semibold text-zinc-300">
                  {isSearching ? 'Письма не найдены' : 'Почтовый ящик пуст'}
                </h3>
                <p className="text-zinc-500 text-xs mt-1">
                  {isSearching 
                    ? 'Попробуйте изменить поисковый запрос.' 
                    : `У вас нет новых непрочитанных писем в аккаунте ${account.toUpperCase()}.`
                  }
                </p>
              </div>
              {isSearching && (
                <button 
                  onClick={handleClearSearch}
                  className="text-xs font-semibold text-blue-400 hover:text-blue-300 transition-colors"
                >
                  Вернуться в Инбокс
                </button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {emails.map((emailItem, idx) => (
                <div 
                  key={idx}
                  className="bg-zinc-900/40 border border-zinc-900 hover:border-zinc-800/80 rounded-2xl p-5 transition-all flex flex-col justify-between group shadow-md hover:shadow-lg"
                >
                  <div className="flex flex-col gap-3.5">
                    {/* Date and Source */}
                    <div className="flex justify-between items-center text-[10px] text-zinc-500 font-mono">
                      <div className="flex items-center gap-1">
                        <Calendar className="h-3 w-3" />
                        <span>{cleanPreviewText(emailItem.date)}</span>
                      </div>
                      <span className="uppercase text-blue-500/80 font-bold bg-blue-500/5 px-2 py-0.5 rounded-lg border border-blue-500/10">
                        {account}
                      </span>
                    </div>

                    {/* Sender */}
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="p-2 rounded-xl bg-zinc-800/60 text-zinc-400 border border-zinc-800 shrink-0">
                        <User className="h-4 w-4" />
                      </div>
                      <div className="min-w-0">
                        <span className="block text-xs font-semibold text-zinc-300 truncate">
                          {cleanPreviewText(emailItem.from)}
                        </span>
                      </div>
                    </div>

                    {/* Subject */}
                    <h2 className="text-sm font-semibold text-zinc-200 tracking-wide line-clamp-2 mt-1">
                      {cleanPreviewText(emailItem.subject)}
                    </h2>

                    {/* Preview */}
                    {emailItem.preview && (
                      <p className="text-xs text-zinc-550 leading-relaxed font-sans line-clamp-3 mt-1.5 min-h-[3rem]">
                        {cleanPreviewText(emailItem.preview)}
                      </p>
                    )}
                  </div>

                  {/* Actions footer */}
                  <div className="flex justify-end gap-2 border-t border-zinc-800/40 pt-4 mt-5">
                    <button
                      onClick={() => handleReplyClick(emailItem)}
                      className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-bold uppercase tracking-wider text-zinc-450 hover:text-blue-400 hover:bg-blue-500/10 transition-all border border-transparent hover:border-blue-500/25 cursor-pointer"
                    >
                      <CornerUpLeft className="h-3.5 w-3.5" />
                      Ответить
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>

      {/* Compose / Edit Form Modal */}
      {isComposeOpen && (
        <div className="fixed inset-0 bg-black/65 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div 
            className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-6 relative flex flex-col gap-5 text-zinc-100 shadow-[0_10px_35px_rgba(0,0,0,0.55)] max-h-[92vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setIsComposeOpen(false)}
              className="absolute top-4 right-4 p-1.5 rounded-lg text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/50 transition-colors"
              title="Закрыть"
            >
              <X className="h-5 w-5" />
            </button>

            {/* Modal Title */}
            <div>
              <h2 className="text-base font-bold text-zinc-200">
                Новое письмо ({account.toUpperCase()})
              </h2>
              <p className="text-zinc-500 text-[11px] mt-0.5">
                Заполните форму для отправки электронного письма через SMTP-сервер
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handlePreviewClick} className="flex flex-col gap-4.5">
              {/* To Recipient */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Получатель (Email) *
                </label>
                <input
                  type="email"
                  required
                  placeholder="name@example.com"
                  value={formState.to}
                  onChange={(e) => setFormState((prev) => ({ ...prev, to: e.target.value }))}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-blue-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all"
                />
              </div>

              {/* Subject */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Тема письма *
                </label>
                <input
                  type="text"
                  required
                  placeholder="Тема"
                  value={formState.subject}
                  onChange={(e) => setFormState((prev) => ({ ...prev, subject: e.target.value }))}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-blue-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all"
                />
              </div>

              {/* Body message */}
              <div>
                <label className="block text-[10px] font-bold text-zinc-500 uppercase tracking-widest mb-1.5">
                  Текст сообщения *
                </label>
                <textarea
                  required
                  placeholder="Напишите текст письма..."
                  rows={6}
                  value={formState.body}
                  onChange={(e) => setFormState((prev) => ({ ...prev, body: e.target.value }))}
                  className="w-full bg-zinc-950 border border-zinc-850 focus:border-blue-500 rounded-xl px-4 py-2.5 text-xs text-zinc-100 placeholder-zinc-500 focus:outline-none transition-all resize-none font-sans"
                />
              </div>

              {/* Action buttons */}
              <div className="flex gap-3 justify-end border-t border-zinc-800/40 pt-4 mt-1.5">
                <button
                  type="button"
                  onClick={() => setIsComposeOpen(false)}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850 transition-colors"
                >
                  Отмена
                </button>
                <button
                  type="submit"
                  className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 active:bg-blue-700 text-zinc-100 rounded-xl px-5 py-2.5 text-xs font-semibold tracking-wide transition-all shadow-md shadow-blue-950/20"
                >
                  <Eye className="h-3.5 w-3.5" />
                  Просмотреть
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Two-step Send Confirmation Preview Modal */}
      {isPreviewOpen && (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-md flex items-center justify-center p-4 z-50">
          <div className="bg-zinc-900 border border-zinc-800 rounded-2xl w-full max-w-lg p-6 relative flex flex-col gap-5 text-zinc-100 shadow-[0_15px_40px_rgba(0,0,0,0.65)] max-h-[92vh] overflow-y-auto animate-scale-in">
            
            {/* Header info */}
            <div className="flex items-center gap-3 border-b border-zinc-800 pb-4">
              <div className="p-2.5 rounded-xl bg-yellow-500/10 text-yellow-500 border border-yellow-500/20">
                <AlertTriangle className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-zinc-200">
                  Подтверждение отправки
                </h2>
                <p className="text-zinc-550 text-[11px] mt-0.5">
                  Внимательно проверьте все данные. Действие совершит реальную отправку письма!
                </p>
              </div>
            </div>

            {/* Email Layout Preview */}
            <div className="flex flex-col gap-4 bg-zinc-950/70 border border-zinc-850 rounded-xl p-5 font-mono text-[11px]">
              <div>
                <span className="text-zinc-500 uppercase font-bold mr-2">Отправитель:</span>
                <span className="text-zinc-350">{account.toUpperCase()} account ({account === 'gmail' ? 'naumov.3111@gmail.com' : 'your_email@ukr.net'})</span>
              </div>
              <div className="border-t border-zinc-900 pt-3">
                <span className="text-zinc-500 uppercase font-bold mr-2">Кому:</span>
                <span className="text-blue-400 font-bold">{formState.to}</span>
              </div>
              <div className="border-t border-zinc-900 pt-3">
                <span className="text-zinc-500 uppercase font-bold mr-2">Тема:</span>
                <span className="text-zinc-200 font-semibold">{formState.subject}</span>
              </div>
              <div className="border-t border-zinc-900 pt-3 flex flex-col gap-2.5">
                <span className="text-zinc-500 uppercase font-bold">Текст письма:</span>
                <pre className="text-zinc-300 font-sans whitespace-pre-wrap leading-relaxed max-h-48 overflow-y-auto bg-zinc-950/20 p-3 rounded-lg border border-zinc-900">
                  {formState.body}
                </pre>
              </div>
            </div>

            {/* Confirmation status feedback */}
            {sendSuccess ? (
              <div className="flex items-center justify-center gap-2 text-emerald-400 text-xs font-semibold py-2">
                <CheckCircle className="h-4.5 w-4.5 animate-bounce" />
                <span>Письмо успешно отправлено!</span>
              </div>
            ) : (
              /* Modal Actions */
              <div className="flex justify-between items-center border-t border-zinc-800/40 pt-4 mt-2">
                <button
                  onClick={() => setIsPreviewOpen(false)}
                  disabled={sending}
                  className="flex items-center gap-1 px-4 py-2 rounded-xl text-xs font-semibold text-zinc-400 hover:text-zinc-200 hover:bg-zinc-850 transition-colors cursor-pointer"
                >
                  <ChevronLeft className="h-4 w-4" />
                  Назад к редактированию
                </button>
                <button
                  onClick={handleRealSend}
                  disabled={sending}
                  className="flex items-center gap-1.5 bg-blue-600 hover:bg-blue-500 disabled:bg-blue-800 text-zinc-100 rounded-xl px-6 py-2.5 text-xs font-bold tracking-wide transition-all shadow-md shadow-blue-900/30 cursor-pointer"
                >
                  {sending ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : (
                    <Send className="h-3.5 w-3.5" />
                  )}
                  {sending ? 'Отправка...' : 'Подтвердить и отправить'}
                </button>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
