import { useState, useEffect, useRef } from 'react';
import { generateSessionId, sendChatMessage, fetchChatHistory } from '../api/chat';
import type { ChatResponse } from '../api/chat';
import { Send, AlertTriangle, AlertCircle, Bot, User } from 'lucide-react';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export default function ChatPage() {
  const [sessionId] = useState<string>(() => generateSessionId());
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>('');
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  
  const [pendingConfirm, setPendingConfirm] = useState<{
    action: string;
    message: string;
  } | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, loading, pendingConfirm]);

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await fetchChatHistory(sessionId);
        const loaded: Message[] = (data.history || []).map((msg: any) => ({
          role: msg.role === 'assistant' ? 'assistant' : 'user',
          content: msg.content || '',
        }));
        setMessages(loaded);
      } catch (err: any) {
        console.warn('Failed to load chat history:', err);
      }
    }
    loadHistory();
  }, [sessionId]);

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim()) return;
    
    setError(null);
    setPendingConfirm(null);
    
    const userMsg: Message = { role: 'user', content: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setLoading(true);

    try {
      const resp: ChatResponse = await sendChatMessage(textToSend, sessionId);
      const assistantMsg: Message = { role: 'assistant', content: resp.response };
      setMessages((prev) => [...prev, assistantMsg]);

      if (resp.requires_confirmation) {
        setPendingConfirm({
          action: resp.tool_calls[0] || 'действие',
          message: resp.response,
        });
      }
    } catch (err: any) {
      setError(err.message || 'Не удалось отправить сообщение. Проверьте соединение с сервером.');
    } finally {
      setLoading(false);
    }
  };

  const handleConfirmAction = (confirm: boolean) => {
    const reply = confirm ? 'да' : 'нет';
    handleSend(reply);
  };

  return (
    <div className="h-full w-full flex flex-col bg-zinc-950 text-zinc-100 font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 bg-zinc-950/60 border-b border-zinc-900 backdrop-blur-md z-10 shrink-0">
        <div className="flex items-center gap-3">
          <div className="h-2 w-2 rounded-full bg-purple-500 shadow-[0_0_8px_#a855f7]"></div>
          <h1 className="text-xl font-bold tracking-tight text-zinc-100 bg-gradient-to-r from-zinc-100 to-zinc-400 bg-clip-text text-transparent">
            Чат с ассистентом
          </h1>
        </div>
        <div className="text-xs text-zinc-500 font-mono hidden md:block">
          Сессия: {sessionId.substring(0, 8)}...
        </div>
      </header>

      {/* Message List Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 min-h-0 relative">
        {messages.length === 0 && !loading && (
          <div className="h-full flex flex-col items-center justify-center text-center text-zinc-500 max-w-sm mx-auto p-8 gap-4 select-none">
            <Bot className="h-10 w-10 text-purple-500/80 animate-bounce" />
            <div>
              <p className="font-semibold text-zinc-300">Добро пожаловать в Home Agent!</p>
              <p className="text-xs text-zinc-500 mt-1.5 leading-relaxed">
                Я могу управлять вашим календарем, читать почту, вести учет финансов и напоминать о дедлайнах. Напишите что-нибудь!
              </p>
            </div>
          </div>
        )}

        {messages.map((msg, index) => {
          const isUser = msg.role === 'user';
          return (
            <div
              key={index}
              className={`flex gap-3 max-w-[85%] md:max-w-[70%] ${
                isUser ? 'ml-auto flex-row-reverse' : 'mr-auto'
              }`}
            >
              <div
                className={`h-8 w-8 rounded-xl flex items-center justify-center shrink-0 border ${
                  isUser
                    ? 'bg-zinc-800 border-zinc-700 text-zinc-300'
                    : 'bg-purple-950/30 border-purple-900/40 text-purple-400'
                }`}
              >
                {isUser ? <User className="h-4.5 w-4.5" /> : <Bot className="h-4.5 w-4.5" />}
              </div>

              <div
                className={`p-3.5 rounded-2xl text-sm leading-relaxed whitespace-pre-wrap ${
                  isUser
                    ? 'bg-purple-600 text-zinc-50 shadow-md shadow-purple-900/10'
                    : 'bg-zinc-900/85 border border-zinc-800 text-zinc-200'
                }`}
              >
                {msg.content}
              </div>
            </div>
          );
        })}

        {loading && (
          <div className="flex gap-3 mr-auto items-center">
            <div className="h-8 w-8 rounded-xl bg-purple-950/30 border border-purple-900/40 text-purple-400 flex items-center justify-center shrink-0">
              <Bot className="h-4.5 w-4.5" />
            </div>
            <div className="p-3.5 bg-zinc-900/85 border border-zinc-800 rounded-2xl flex items-center gap-1.5 shadow-sm">
              <span className="h-2 w-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></span>
              <span className="h-2 w-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></span>
              <span className="h-2 w-2 bg-zinc-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></span>
            </div>
          </div>
        )}

        {pendingConfirm && (
          <div className="max-w-[85%] md:max-w-[70%] mr-auto ml-11 p-4 bg-yellow-950/20 border border-yellow-800/40 rounded-2xl flex flex-col gap-3 shadow-lg backdrop-blur-sm z-10 animate-in fade-in duration-300">
            <div className="flex items-center gap-2.5 text-yellow-400 text-xs font-semibold">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>Требуется подтверждение действия</span>
            </div>
            <p className="text-xs text-zinc-300 leading-relaxed">
              Вы хотите выполнить это действие? Оно помечено как RED-действие.
            </p>
            <div className="flex gap-2 mt-1">
              <button
                onClick={() => handleConfirmAction(true)}
                className="flex-1 py-1.5 px-3 bg-yellow-600 hover:bg-yellow-500 active:bg-yellow-750 text-zinc-950 text-xs font-bold rounded-lg transition-colors cursor-pointer"
              >
                Да, разрешить
              </button>
              <button
                onClick={() => handleConfirmAction(false)}
                className="flex-1 py-1.5 px-3 bg-zinc-900 border border-zinc-800 hover:bg-zinc-800 active:bg-zinc-950 text-zinc-300 text-xs font-semibold rounded-lg transition-colors cursor-pointer"
              >
                Нет, отменить
              </button>
            </div>
          </div>
        )}

        {error && (
          <div className="max-w-md mx-auto p-4 bg-red-950/20 border border-red-800/30 rounded-2xl flex flex-col items-center text-center gap-3 shadow-md z-10 animate-in zoom-in duration-200">
            <AlertCircle className="h-8 w-8 text-red-500/90" />
            <div className="flex flex-col gap-1">
              <p className="text-sm font-semibold text-red-400">Ошибка сети</p>
              <p className="text-xs text-zinc-400 leading-normal">{error}</p>
            </div>
            <button
              onClick={() => {
                setError(null);
                if (messages.length > 0) {
                  const lastUserMessage = [...messages].reverse().find(m => m.role === 'user');
                  if (lastUserMessage) {
                    handleSend(lastUserMessage.content);
                  }
                }
              }}
              className="py-1.5 px-4 bg-zinc-850 hover:bg-zinc-800 border border-zinc-700 hover:border-zinc-600 active:bg-zinc-900 text-zinc-300 text-xs font-semibold rounded-lg transition-all cursor-pointer"
            >
              Попробовать снова
            </button>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <footer className="p-4 bg-zinc-950 border-t border-zinc-900 shrink-0">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSend(input);
          }}
          className="max-w-4xl mx-auto flex items-center gap-2.5"
        >
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder={loading ? 'Ожидание ответа...' : 'Спросите ассистента...'}
            className="flex-1 px-4 py-3 bg-zinc-900/70 border border-zinc-850 focus:border-purple-650 rounded-2xl text-sm text-zinc-200 placeholder-zinc-500 outline-none transition-all disabled:opacity-60"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="p-3 bg-purple-600 hover:bg-purple-500 active:bg-purple-750 text-zinc-50 rounded-2xl transition-all disabled:opacity-50 disabled:pointer-events-none cursor-pointer"
          >
            <Send className="h-4.5 w-4.5" />
          </button>
        </form>
      </footer>
    </div>
  );
}
