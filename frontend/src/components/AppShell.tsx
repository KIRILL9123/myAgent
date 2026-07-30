import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Brain, Calendar, CheckCircle2, Clock, LayoutDashboard, Mail, Menu,
  MessageSquare, ShieldCheck, Wallet, X,
} from 'lucide-react';

interface AppShellProps { children: React.ReactNode; }

const NAV_ITEMS = [
  { path: '/dashboard', label: 'Обзор', icon: LayoutDashboard, mobile: 'Обзор', primary: true },
  { path: '/chat', label: 'Чат', icon: MessageSquare, mobile: 'Чат', primary: true },
  { path: '/calendar', label: 'Календарь', icon: Calendar, mobile: 'Календарь', primary: true },
  { path: '/mail', label: 'Почта', icon: Mail, mobile: 'Почта', primary: false },
  { path: '/finance', label: 'Финансы', icon: Wallet, mobile: 'Финансы', primary: false },
  { path: '/deadlines', label: 'Дедлайны', icon: Clock, mobile: 'Дедлайны', primary: false },
  { path: '/memory', label: 'Память', icon: Brain, mobile: 'Память', primary: false },
  { path: '/commitments', label: 'Обязательства', icon: CheckCircle2, mobile: 'Обязательства', primary: true },
  { path: '/approvals', label: 'Подтверждения', icon: ShieldCheck, mobile: 'Подтверждения', primary: false },
];

export default function AppShell({ children }: AppShellProps) {
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const isActive = (path: string) => location.pathname === path;
  const primaryItems = NAV_ITEMS.filter(item => item.primary);
  const secondaryItems = NAV_ITEMS.filter(item => !item.primary);
  const secondaryActive = secondaryItems.some(item => isActive(item.path));

  useEffect(() => { setMoreOpen(false); }, [location.pathname]);

  const navLink = (item: typeof NAV_ITEMS[number], mobile = false) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    return (
      <Link
        key={item.path}
        to={item.path}
        className={mobile
          ? `flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-1 py-1.5 transition-colors ${active ? 'text-purple-300' : 'text-zinc-500 hover:text-zinc-200'}`
          : `flex items-center gap-3.5 rounded-xl px-4 py-3 text-xs font-semibold transition-all ${active ? 'bg-purple-650 text-zinc-100 shadow-lg shadow-purple-900/20' : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'}`}
      >
        <Icon className={mobile ? 'h-5 w-5' : 'h-4.5 w-4.5 shrink-0'} />
        <span className={mobile ? 'max-w-full truncate text-[10px]' : ''}>{mobile ? item.mobile : item.label}</span>
      </Link>
    );
  };

  return (
    <div className="flex h-[100dvh] min-h-[100dvh] w-screen flex-col overflow-hidden bg-zinc-950 font-sans text-zinc-100 sm:flex-row">
      <aside className="hidden w-64 shrink-0 flex-col gap-6 border-r border-zinc-800 bg-zinc-900 p-5 select-none sm:flex">
        <div className="flex items-center gap-3 px-2 py-3">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-650 text-xs font-bold text-white shadow-[0_0_12px_#a855f7]">HA</div>
          <span className="font-mono text-sm font-bold uppercase tracking-wide text-zinc-200">Home Agent</span>
        </div>
        <nav className="flex flex-col gap-2">{NAV_ITEMS.map(item => navLink(item))}</nav>
        <div className="mt-auto border-t border-zinc-800 px-4 py-3 font-mono text-[10px] text-zinc-500">v0.2.0 · Active Session</div>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 flex-1 overflow-hidden">{children}</div>

        {moreOpen && (
          <div className="absolute inset-x-3 bottom-[4.75rem] z-40 rounded-2xl border border-zinc-700 bg-zinc-900/95 p-2 shadow-2xl backdrop-blur-xl sm:hidden">
            <div className="mb-1 flex items-center justify-between px-3 py-2 text-xs font-semibold text-zinc-300">
              <span>Ещё разделы</span>
              <button onClick={() => setMoreOpen(false)} className="rounded-lg p-1 text-zinc-500 hover:text-zinc-200"><X className="h-4 w-4" /></button>
            </div>
            <div className="grid grid-cols-2 gap-1">{secondaryItems.map(item => navLink(item, true))}</div>
          </div>
        )}

        <nav className="z-30 flex shrink-0 items-center gap-1 border-t border-zinc-800 bg-zinc-900/95 px-2 pb-[env(safe-area-inset-bottom)] pt-1.5 backdrop-blur-md sm:hidden">
          {primaryItems.map(item => navLink(item, true))}
          <button onClick={() => setMoreOpen(value => !value)} className={`flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-1 py-1.5 ${moreOpen || secondaryActive ? 'text-purple-300' : 'text-zinc-500'}`}>
            {moreOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            <span className="text-[10px]">Ещё</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
