import { useEffect, useRef, useState } from 'react';
import { AlertCircle, AlertTriangle, Bot, Check, Loader2, Send, User, X } from 'lucide-react';
import { ThinkingOrb } from 'thinking-orbs';
import { sendChatMessage, fetchChatHistory } from '../api/chat';
import type { ChatResponse } from '../api/chat';
import WeatherCard from '../components/WeatherCard';
import WebSourcesCard from '../components/WebSourcesCard';

interface Message {
  role: 'user' | 'assistant';
  content: string;
  weather?: ChatResponse['weather'];
  webSources?: ChatResponse['web_sources'];
  memoryUsed?: ChatResponse['memory_used'];
  documentsUsed?: ChatResponse['documents_used'];
}

interface ChatPageProps { sessionId: string; }

const SUGGESTIONS = ['Что у меня сегодня?', 'Покажи ближайшие дедлайны', 'Собери непрочитанные письма', 'Запомни важную мысль'];
type ThinkingState = 'working' | 'searching' | 'connecting';

function getThinkingState(text: string): ThinkingState {
  const normalized = text.toLowerCase();
  if (/(календар|почт|телеграм|telegram|финанс|подпис)/.test(normalized)) return 'connecting';
  if (/(покажи|найди|поиск|ищи|проверь|список|что у меня)/.test(normalized)) return 'searching';
  return 'working';
}

const THINKING_LABELS: Record<ThinkingState, string> = {
  working: 'Mira обрабатывает запрос',
  searching: 'Mira ищет нужную информацию',
  connecting: 'Mira обращается к подключённым данным',
};

function AssistantDetails({ message }: { message: Message }) {
  return (
    <>
      {message.weather && <div className="mt-4"><WeatherCard weather={message.weather} /></div>}
      {message.webSources && <WebSourcesCard sources={message.webSources} />}
      {message.documentsUsed && message.documentsUsed.length > 0 && <details className="chat-meta-details"><summary>Использованы документы: {message.documentsUsed.length}</summary><ul>{message.documentsUsed.map(item => <li key={`${item.document_id}-${item.chunk_id}`}>{item.document_name}</li>)}</ul></details>}
      {message.memoryUsed && message.memoryUsed.length > 0 && <details className="chat-meta-details"><summary>Использовано из памяти: {message.memoryUsed.length}</summary><ul>{message.memoryUsed.map(item => <li key={`${item.type}-${item.id}`}>{item.type === 'note' ? 'Заметка: ' : 'Факт: '}{item.title}</li>)}</ul></details>}
    </>
  );
}

export default function ChatPage({ sessionId }: ChatPageProps) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [thinkingState, setThinkingState] = useState<ThinkingState>('working');
  const [pendingConfirm, setPendingConfirm] = useState<{ action: string; message: string } | null>(null);
  const [confirming, setConfirming] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, loading, pendingConfirm]);

  useEffect(() => {
    async function loadHistory() {
      try {
        const data = await fetchChatHistory(sessionId);
        setMessages((data.history || []).map((message: any) => ({ role: message.role === 'assistant' ? 'assistant' : 'user', content: message.content || '' })));
      } catch (historyError) {
        console.warn('Failed to load chat history:', historyError);
      }
    }
    loadHistory();
  }, [sessionId]);

  const appendResponse = (response: ChatResponse) => {
    const assistantMessage: Message = { role: 'assistant', content: response.response, weather: response.weather, webSources: response.web_sources, memoryUsed: response.memory_used, documentsUsed: response.documents_used };
    setMessages(current => [...current, assistantMessage]);
    if (response.requires_confirmation) setPendingConfirm({ action: response.tool_calls[0] || 'действие', message: response.response });
    else setPendingConfirm(null);
  };

  const handleSend = async (textToSend: string) => {
    if (!textToSend.trim() || loading) return;
    setError(null); setPendingConfirm(null); setMessages(current => [...current, { role: 'user', content: textToSend }]); setInput(''); setThinkingState(getThinkingState(textToSend)); setLoading(true);
    try { appendResponse(await sendChatMessage(textToSend, sessionId)); }
    catch (requestError: any) { setError(requestError.message || 'Не удалось отправить сообщение. Проверьте соединение с сервером.'); }
    finally { setLoading(false); setThinkingState('working'); }
  };

  const handleConfirmAction = async (confirm: boolean) => {
    if (!pendingConfirm) return;
    setError(null); setThinkingState('working'); setConfirming(true);
    try { appendResponse(await sendChatMessage(confirm ? 'да' : 'нет', sessionId)); }
    catch (requestError: any) { setError(requestError.message || 'Не удалось отправить подтверждение. Проверьте соединение с сервером.'); }
    finally { setConfirming(false); setThinkingState('working'); }
  };

  return (
    <div className="chat-page">
      <header className="chat-header">
        <div className="chat-title-block"><div className="chat-avatar"><Bot className="h-4 w-4" aria-hidden="true" /></div><div><h1>Ассистент</h1><p>Локальная рабочая сессия</p></div></div>
        <span className="session-chip">Сессия {sessionId.substring(0, 8)}</span>
      </header>

      <main className="chat-scroll" aria-live="polite">
        {messages.length === 0 && !loading && (
          <div className="chat-empty">
            <div className="chat-empty-icon"><Bot className="h-6 w-6" aria-hidden="true" /></div>
            <h2>Чем займёмся?</h2>
            <p>Спросите о делах, календаре, почте, финансах или памяти — я помогу собрать всё в одну понятную картину.</p>
            <div className="chat-suggestions">{SUGGESTIONS.map(suggestion => <button key={suggestion} type="button" className="chat-suggestion" onClick={() => setInput(suggestion)}>{suggestion}</button>)}</div>
          </div>
        )}

        {messages.map((message, index) => {
          const isUser = message.role === 'user';
          return <div key={index} className={`chat-message ${isUser ? 'chat-message-user' : ''}`}>
            <div className={`chat-message-avatar ${isUser ? '' : 'chat-message-avatar-assistant'}`}>{isUser ? <User className="h-3.5 w-3.5" aria-hidden="true" /> : <Bot className="h-3.5 w-3.5" aria-hidden="true" />}</div>
            <div className={`chat-bubble ${isUser ? 'chat-bubble-user' : 'chat-bubble-assistant'}`}>{message.content}{!isUser && <AssistantDetails message={message} />}</div>
          </div>;
        })}

        {loading && <div className="chat-typing"><div className="chat-message-avatar chat-message-avatar-assistant"><Bot className="h-3.5 w-3.5" aria-hidden="true" /></div><div className="chat-typing-bubble" aria-label={THINKING_LABELS[thinkingState]}><ThinkingOrb state={thinkingState} size={20} theme="dark" aria-label={THINKING_LABELS[thinkingState]} /></div></div>}

        {pendingConfirm && <div className="chat-confirmation"><div className="chat-confirmation-heading"><AlertTriangle className="h-4 w-4" aria-hidden="true" />Требуется подтверждение действия</div><p>{pendingConfirm.message}<br /><span className="opacity-80">Действие: {pendingConfirm.action}</span></p><div className="chat-confirmation-actions"><button type="button" className="ui-button ui-button-primary" onClick={() => handleConfirmAction(true)} disabled={confirming}>{confirming ? <Loader2 className="h-4 w-4 animate-spin" /> : <Check className="h-4 w-4" />}Разрешить</button><button type="button" className="ui-button ui-button-neutral" onClick={() => handleConfirmAction(false)} disabled={confirming}><X className="h-4 w-4" />Отменить</button></div></div>}

        {error && <div className="chat-error"><AlertCircle className="h-5 w-5 shrink-0" aria-hidden="true" /><span>{error}</span><button type="button" className="ui-button ui-button-neutral" onClick={() => { setError(null); const lastUserMessage = [...messages].reverse().find(message => message.role === 'user'); if (lastUserMessage) handleSend(lastUserMessage.content); }}>Повторить</button></div>}
        <div ref={messagesEndRef} />
      </main>

      <footer className="chat-composer-wrap"><form className="chat-composer" onSubmit={(event) => { event.preventDefault(); handleSend(input); }}><textarea value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); handleSend(input); } }} disabled={loading} rows={1} placeholder={loading ? 'Ожидание ответа…' : 'Напишите сообщение…'} aria-label="Сообщение ассистенту" /><button type="submit" className="chat-send" disabled={loading || !input.trim()} aria-label="Отправить сообщение"><Send className="h-4 w-4" aria-hidden="true" /></button></form></footer>
    </div>
  );
}
