import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { MessageSquare, Calendar, Mail, Wallet, Clock, Brain } from 'lucide-react';

interface AppShellProps {
  children: React.ReactNode;
}

const NAV_ITEMS = [
  { path: '/chat', label: 'Чат', icon: MessageSquare },
  { path: '/calendar', label: 'Календарь', icon: Calendar },
  { path: '/mail', label: 'Почта', icon: Mail },
  { path: '/finance', label: 'Финансы', icon: Wallet },
  { path: '/deadlines', label: 'Дедлайны', icon: Clock },
  { path: '/memory', label: 'Память', icon: Brain },
];

export default function AppShell({ children }: AppShellProps) {
  const location = useLocation();

  const isActive = (path: string) => {
    return location.pathname === path;
  };

  return (
    <div className="h-screen w-screen flex flex-col sm:flex-row bg-zinc-950 text-zinc-100 overflow-hidden font-sans">
      {/* Desktop Left Sidebar Navigation */}
      <aside className="hidden sm:flex flex-col w-64 bg-zinc-900 border-r border-zinc-800 p-5 gap-6 select-none shrink-0">
        <div className="flex items-center gap-3 px-2 py-3">
          <div className="h-6 w-6 rounded-lg bg-purple-650 shadow-[0_0_12px_#a855f7] flex items-center justify-center font-bold text-xs text-white">
            HA
          </div>
          <span className="font-bold text-sm tracking-wide text-zinc-200 uppercase font-mono">
            Home Agent
          </span>
        </div>

        <nav className="flex flex-col gap-2">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex items-center gap-3.5 px-4 py-3 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                  active
                    ? 'bg-purple-650 text-zinc-100 shadow-lg shadow-purple-900/20'
                    : 'text-zinc-400 hover:text-zinc-200 hover:bg-zinc-800/40'
                }`}
              >
                <Icon className="h-4.5 w-4.5 shrink-0" />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        <div className="mt-auto px-4 py-3 border-t border-zinc-800 text-[10px] text-zinc-500 font-mono">
          v0.2.0 • Active Session
        </div>
      </aside>

      {/* Main Page Area */}
      <div className="flex-1 flex flex-col min-w-0 relative">
        <div className="flex-1 overflow-hidden relative">
          {children}
        </div>
        
        {/* Mobile Bottom Navigation Bar */}
        <nav className="sm:hidden flex bg-zinc-900/90 border-t border-zinc-800 backdrop-blur-md justify-around items-center py-2 px-1 z-30 select-none">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const active = isActive(item.path);
            return (
              <Link
                key={item.path}
                to={item.path}
                className={`flex flex-col items-center gap-1.5 py-1 px-3.5 rounded-xl transition-all cursor-pointer ${
                  active ? 'text-purple-400 font-semibold' : 'text-zinc-500 hover:text-zinc-300'
                }`}
              >
                <Icon className="h-5 w-5" />
                <span className="text-[9px] tracking-wide">{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </div>
  );
}
