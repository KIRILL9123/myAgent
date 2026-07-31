import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Brain, Calendar, CheckCircle2, ChevronDown, Clock, CreditCard,
  LayoutDashboard, ListTodo, Mail, Menu, MessageSquare, MonitorCog,
  ShieldCheck, Sparkles, Wallet, X,
} from 'lucide-react';

interface AppShellProps { children: React.ReactNode; }

interface NavItem {
  path: string;
  label: string;
  mobile: string;
  icon: typeof LayoutDashboard;
}

interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

const HOME: NavItem = { path: '/dashboard', label: 'Главная', mobile: 'Главная', icon: LayoutDashboard };
const CHAT: NavItem = { path: '/chat', label: 'Чат', mobile: 'Чат', icon: MessageSquare };

const NAV_GROUPS: NavGroup[] = [
  {
    id: 'planning',
    label: 'Планирование',
    items: [
      { path: '/calendar', label: 'Календарь', mobile: 'Календарь', icon: Calendar },
      { path: '/deadlines', label: 'Дедлайны', mobile: 'Дедлайны', icon: Clock },
      { path: '/commitments', label: 'Обязательства', mobile: 'Обязательства', icon: CheckCircle2 },
    ],
  },
  {
    id: 'communication',
    label: 'Коммуникации',
    items: [{ path: '/mail', label: 'Почта', mobile: 'Почта', icon: Mail }],
  },
  {
    id: 'money',
    label: 'Деньги',
    items: [
      { path: '/finance', label: 'Финансы', mobile: 'Финансы', icon: Wallet },
      { path: '/subscriptions', label: 'Подписки', mobile: 'Подписки', icon: CreditCard },
    ],
  },
  {
    id: 'intelligence',
    label: 'Интеллект',
    items: [
      { path: '/memory', label: 'Память', mobile: 'Память', icon: Brain },
      { path: '/state', label: 'Состояние', mobile: 'Состояние', icon: Sparkles },
    ],
  },
  {
    id: 'control',
    label: 'Центр контроля',
    items: [
      { path: '/approvals', label: 'Подтверждения', mobile: 'Подтверждения', icon: ShieldCheck },
      { path: '/system', label: 'Система', mobile: 'Система', icon: MonitorCog },
    ],
  },
];

const ALL_SECONDARY_ITEMS = NAV_GROUPS.flatMap(group => group.items);

export default function AppShell({ children }: AppShellProps) {
  const location = useLocation();
  const [moreOpen, setMoreOpen] = useState(false);
  const [openGroups, setOpenGroups] = useState<Record<string, boolean>>({ planning: true });
  const isActive = (path: string) => location.pathname === path;
  const isGroupActive = (group: NavGroup) => group.items.some(item => isActive(item.path));
  const activeGroupId = NAV_GROUPS.find(group => isGroupActive(group))?.id;

  useEffect(() => {
    setMoreOpen(false);
    if (activeGroupId) setOpenGroups(current => ({ ...current, [activeGroupId]: true }));
  }, [location.pathname, activeGroupId]);

  const navLink = (item: NavItem, mobile = false) => {
    const Icon = item.icon;
    const active = isActive(item.path);
    return (
      <Link
        key={item.path}
        to={item.path}
        className={mobile
          ? `flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-1 py-1.5 transition-colors ${active ? 'text-purple-300' : 'text-zinc-500 hover:text-zinc-200'}`
          : `flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-xs font-semibold transition-all ${active ? 'bg-purple-650 text-zinc-100 shadow-lg shadow-purple-900/20' : 'text-zinc-400 hover:bg-zinc-800/40 hover:text-zinc-200'}`}
      >
        <Icon className={mobile ? 'h-5 w-5' : 'h-4 w-4 shrink-0'} />
        <span className={mobile ? 'max-w-full truncate text-[10px]' : ''}>{mobile ? item.mobile : item.label}</span>
      </Link>
    );
  };

  const groupNav = (group: NavGroup) => {
    const open = Boolean(openGroups[group.id]);
    const active = isGroupActive(group);
    return (
      <div key={group.id}>
        <button
          type="button"
          onClick={() => setOpenGroups(current => ({ ...current, [group.id]: !open }))}
          className={`flex w-full items-center justify-between rounded-xl px-3.5 py-2 text-[10px] font-bold uppercase tracking-wider transition-colors ${active ? 'text-purple-200' : 'text-zinc-500 hover:bg-zinc-800/30 hover:text-zinc-300'}`}
          aria-expanded={open}
        >
          <span>{group.label}</span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} />
        </button>
        {open && <div className="mt-1 space-y-1 pl-1">{group.items.map(item => navLink(item))}</div>}
      </div>
    );
  };

  const mobileMoreContent = NAV_GROUPS.map(group => (
    <React.Fragment key={group.id}>
      <div className="col-span-2 px-3 pb-1 pt-2 text-[10px] font-bold uppercase tracking-wider text-zinc-600">{group.label}</div>
      {group.items.map(item => navLink(item, true))}
    </React.Fragment>
  ));

  const secondaryActive = ALL_SECONDARY_ITEMS.some(item => isActive(item.path));

  return (
    <div className="flex h-[100dvh] min-h-[100dvh] w-screen flex-col overflow-hidden bg-zinc-950 font-sans text-zinc-100 sm:flex-row">
      <aside className="hidden w-64 shrink-0 flex-col border-r border-zinc-800 bg-zinc-900 p-5 select-none sm:flex">
        <div className="flex items-center gap-3 px-2 py-3">
          <div className="flex h-6 w-6 items-center justify-center rounded-lg bg-purple-650 text-xs font-bold text-white shadow-[0_0_12px_#a855f7]">HA</div>
          <span className="font-mono text-sm font-bold uppercase tracking-wide text-zinc-200">Home Agent</span>
        </div>
        <nav className="mt-4 flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto pr-1">
          <div className="space-y-1">{navLink(HOME)}{navLink(CHAT)}</div>
          {NAV_GROUPS.map(groupNav)}
        </nav>
        <div className="mt-4 border-t border-zinc-800 px-4 py-3 font-mono text-[10px] text-zinc-500">v0.2.0 · Active Session</div>
      </aside>

      <div className="relative flex min-w-0 flex-1 flex-col overflow-hidden">
        <div className="min-h-0 flex-1 overflow-hidden">{children}</div>

        {moreOpen && (
          <div className="absolute inset-x-3 bottom-[4.75rem] z-40 max-h-[70dvh] overflow-y-auto rounded-2xl border border-zinc-700 bg-zinc-900/95 p-2 shadow-2xl backdrop-blur-xl sm:hidden">
            <div className="mb-1 flex items-center justify-between px-3 py-2 text-xs font-semibold text-zinc-300">
              <span>Все разделы</span>
              <button onClick={() => setMoreOpen(false)} aria-label="Закрыть меню разделов" className="rounded-lg p-1 text-zinc-500 hover:text-zinc-200"><X className="h-4 w-4" /></button>
            </div>
            <div className="grid grid-cols-2 gap-1">{mobileMoreContent}</div>
          </div>
        )}

        <nav className="z-30 flex shrink-0 items-center gap-1 border-t border-zinc-800 bg-zinc-900/95 px-2 pb-[env(safe-area-inset-bottom)] pt-1.5 backdrop-blur-md sm:hidden">
          {navLink(HOME, true)}
          {navLink(CHAT, true)}
          {navLink({ path: '/commitments', label: 'Задачи', mobile: 'Задачи', icon: ListTodo }, true)}
          <button onClick={() => setMoreOpen(value => !value)} aria-expanded={moreOpen} aria-label="Открыть все разделы" className={`flex min-w-0 flex-1 flex-col items-center gap-1 rounded-xl px-1 py-1.5 ${moreOpen || secondaryActive ? 'text-purple-300' : 'text-zinc-500'}`}>
            {moreOpen ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
            <span className="text-[10px]">Ещё</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
