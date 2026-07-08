import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import ChatPage from './pages/ChatPage';
import MemoryPage from './pages/MemoryPage';

const PlaceholderPage = ({ title }: { title: string }) => (
  <div className="h-full w-full flex flex-col items-center justify-center bg-zinc-950 text-zinc-500 font-sans select-none">
    <div className="text-center space-y-2">
      <h1 className="text-xl font-bold text-zinc-400">{title}</h1>
      <p className="text-xs text-zinc-650">Этот раздел находится в разработке...</p>
    </div>
  </div>
);

function App() {
  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/calendar" element={<PlaceholderPage title="Календарь" />} />
          <Route path="/mail" element={<PlaceholderPage title="Почта" />} />
          <Route path="/finance" element={<PlaceholderPage title="Финансы" />} />
          <Route path="/deadlines" element={<PlaceholderPage title="Дедлайны" />} />
          <Route path="*" element={<Navigate to="/chat" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
