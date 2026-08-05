import { lazy, Suspense, useCallback, useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import QueryProvider from './components/QueryProvider';
import { generateSessionId } from './api/chat';

const DashboardPage = lazy(() => import('./pages/DashboardPage'));
const ChatPage = lazy(() => import('./pages/ChatPage'));
const MemoryPage = lazy(() => import('./pages/MemoryPage'));
const DocumentsPage = lazy(() => import('./pages/DocumentsPage'));
const CommitmentsPage = lazy(() => import('./pages/CommitmentsPage'));
const ApprovalsPage = lazy(() => import('./pages/ApprovalsPage'));
const NotificationsPage = lazy(() => import('./pages/NotificationsPage'));
const NotificationPreferencesPage = lazy(() => import('./pages/NotificationPreferencesPage'));
const ErrorsPage = lazy(() => import('./pages/ErrorsPage'));
const SystemPage = lazy(() => import('./pages/SystemPage'));
const CalendarPage = lazy(() => import('./pages/CalendarPage'));
const MailPage = lazy(() => import('./pages/MailPage'));
const FinancePage = lazy(() => import('./pages/FinancePage'));
const CountdownsPage = lazy(() => import('./pages/CountdownsPage'));
const SubscriptionsPage = lazy(() => import('./pages/SubscriptionsPage'));
const StatePage = lazy(() => import('./pages/StatePage'));
const SandboxPage = lazy(() => import('./pages/SandboxPage'));

function PageFallback() {
  return (
    <div className="flex min-h-[50vh] items-center justify-center text-zinc-400">
      <div className="state-box min-h-0 border-solid px-5 py-4">
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-zinc-600 border-t-emerald-400" />
        <span>Загрузка раздела…</span>
      </div>
    </div>
  );
}

function App() {
  const [sessionId, setSessionId] = useState<string>(() => generateSessionId());
  const startNewChat = useCallback(() => {
    setSessionId(generateSessionId());
  }, []);

  return (
    <BrowserRouter>
      <QueryProvider>
        <AppShell onNewChat={startNewChat}>
        <Suspense fallback={<PageFallback />}>
          <Routes>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/chat" element={<ChatPage key={sessionId} sessionId={sessionId} />} />
            <Route path="/memory" element={<MemoryPage />} />
            <Route path="/documents" element={<DocumentsPage />} />
            <Route path="/commitments" element={<CommitmentsPage />} />
            <Route path="/approvals" element={<ApprovalsPage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
            <Route path="/notifications/preferences" element={<NotificationPreferencesPage />} />
            <Route path="/errors" element={<ErrorsPage />} />
            <Route path="/system" element={<SystemPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/mail" element={<MailPage />} />
            <Route path="/finance" element={<FinancePage />} />
            <Route path="/deadlines" element={<CountdownsPage />} />
            <Route path="/subscriptions" element={<SubscriptionsPage />} />
            <Route path="/state" element={<StatePage />} />
            <Route path="/sandbox" element={<SandboxPage />} />
            <Route path="*" element={<Navigate to="/dashboard" replace />} />
          </Routes>
        </Suspense>
        </AppShell>
      </QueryProvider>
    </BrowserRouter>
  );
}

export default App;
