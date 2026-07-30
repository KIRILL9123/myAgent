import { useState } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import AppShell from './components/AppShell';
import ChatPage from './pages/ChatPage';
import MemoryPage from './pages/MemoryPage';
import CalendarPage from './pages/CalendarPage';
import MailPage from './pages/MailPage';
import FinancePage from './pages/FinancePage';
import CountdownsPage from './pages/CountdownsPage';
import DashboardPage from './pages/DashboardPage';
import CommitmentsPage from './pages/CommitmentsPage';
import ApprovalsPage from './pages/ApprovalsPage';
import SystemPage from './pages/SystemPage';
import { generateSessionId } from './api/chat';

function App() {
  const [sessionId] = useState<string>(() => generateSessionId());

  return (
    <BrowserRouter>
      <AppShell>
        <Routes>
          <Route path="/dashboard" element={<DashboardPage />} />
          <Route path="/chat" element={<ChatPage sessionId={sessionId} />} />
          <Route path="/memory" element={<MemoryPage />} />
          <Route path="/commitments" element={<CommitmentsPage />} />
          <Route path="/approvals" element={<ApprovalsPage />} />
          <Route path="/system" element={<SystemPage />} />
          <Route path="/calendar" element={<CalendarPage />} />
          <Route path="/mail" element={<MailPage />} />
          <Route path="/finance" element={<FinancePage />} />
          <Route path="/deadlines" element={<CountdownsPage />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AppShell>
    </BrowserRouter>
  );
}

export default App;
