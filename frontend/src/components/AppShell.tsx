import React, { useEffect, useRef, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  Bell,
  Brain,
  Calendar,
  CheckCircle2,
  ChevronDown,
  FileStack,
  LayoutDashboard,
  Mail,
  Menu,
  MessageSquare,
  Plus,
  Upload,
  WalletCards,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { DOCUMENT_ACCEPT, uploadDocument } from '../api/documents';

interface AppShellProps { children: React.ReactNode; onNewChat: () => void; }

interface NavItem {
  path: string;
  label: string;
  mobile: string;
  icon: LucideIcon;
}

interface NavGroup {
  id: string;
  label: string;
  items: NavItem[];
}

const HOME: NavItem = { path: '/dashboard', label: 'Главная', mobile: 'Главная', icon: LayoutDashboard };
const CHAT: NavItem = { path: '/chat', label: 'Чат', mobile: 'Чат', icon: MessageSquare };
const NOTIFICATIONS: NavItem = { path: '/notifications', label: 'Центр уведомлений', mobile: 'Уведомления', icon: Bell };
const MAIL: NavItem = { path: '/mail', label: 'Почта', mobile: 'Почта', icon: Mail };
const TASKS: NavItem = { path: '/commitments', label: 'Обязательства', mobile: 'Задачи', icon: CheckCircle2 };

const NAV_GROUPS: NavGroup[] = [
  {
    id: 'planning',
    label: 'Планирование',
    items: [
      { path: '/calendar', label: 'Календарь', mobile: 'Календарь', icon: Calendar },
      TASKS,
    ],
  },
  {
    id: 'money',
    label: 'Финансы',
    items: [
      { path: '/finance', label: 'Финансы', mobile: 'Финансы', icon: WalletCards },
    ],
  },
  {
    id: 'intelligence',
    label: 'Знания',
    items: [
      { path: '/memory', label: 'Память', mobile: 'Память', icon: Brain },
      { path: '/documents', label: 'Документы', mobile: 'Документы', icon: FileStack },
    ],
  },
];

const ALL_SECONDARY_ITEMS = [NOTIFICATIONS, MAIL, ...NAV_GROUPS.flatMap(group => group.items)];

function MobileUploadAction() {
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [feedback, setFeedback] = useState<string | null>(null);

  const upload = async (file: File) => {
    setBusy(true);
    setFeedback(null);
    try {
      const item = await uploadDocument(file);
      setFeedback(item.status === 'ready' ? `Добавлен: ${item.original_name}` : 'Файл добавлен, но не обработан');
    } catch (error) {
      setFeedback(error instanceof Error ? error.message : 'Не удалось загрузить файл');
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = '';
      window.setTimeout(() => setFeedback(null), 4000);
    }
  };

  return (
    <>
      <input ref={inputRef} type="file" accept={DOCUMENT_ACCEPT} className="mobile-upload-input" onChange={event => { const file = event.target.files?.[0]; if (file) void upload(file); }} />
      <button type="button" onClick={() => inputRef.current?.click()} disabled={busy} aria-busy={busy} aria-label="Загрузить файл" className="mobile-nav-link mobile-nav-upload">
        <Upload className="shell-nav-icon" aria-hidden="true" />
        <span>{busy ? 'Загрузка' : 'Загрузить'}</span>
      </button>
      {feedback && <div className="mobile-upload-feedback" role="status">{feedback}</div>}
    </>
  );
}

export default function AppShell({ children, onNewChat }: AppShellProps) {
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
        aria-current={active ? 'page' : undefined}
        data-active={active}
        className={mobile ? 'mobile-nav-link' : 'shell-nav-link'}
      >
        <Icon className="shell-nav-icon" aria-hidden="true" />
        <span>{mobile ? item.mobile : item.label}</span>
      </Link>
    );
  };

  const groupNav = (group: NavGroup) => {
    const open = Boolean(openGroups[group.id]);
    const active = isGroupActive(group);
    return (
      <div key={group.id} className="shell-nav-group">
        <button
          type="button"
          onClick={() => setOpenGroups(current => ({ ...current, [group.id]: !open }))}
          className="shell-nav-section"
          aria-expanded={open}
          data-active={active}
        >
          <span>{group.label}</span>
          <ChevronDown className={`h-3.5 w-3.5 transition-transform ${open ? 'rotate-180' : ''}`} aria-hidden="true" />
        </button>
        {open && <div className="shell-nav-items">{group.items.map(item => navLink(item))}</div>}
      </div>
    );
  };

  const mobileMoreContent = (
    <>
      <div className="mobile-nav-section-title">Обзор</div>
      {navLink(HOME, true)}
      {navLink(MAIL, true)}
      {NAV_GROUPS.map(group => (
        <React.Fragment key={group.id}>
          <div className="mobile-nav-section-title">{group.label}</div>
          {group.items.filter(item => item.path !== TASKS.path).map(item => navLink(item, true))}
        </React.Fragment>
      ))}
    </>
  );

  const secondaryActive = ALL_SECONDARY_ITEMS.some(item => isActive(item.path));
  const moreActive = secondaryActive && ![TASKS.path, NOTIFICATIONS.path].includes(location.pathname);
  const handleNewChatClick = (event: React.MouseEvent<HTMLAnchorElement>) => {
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    onNewChat();
  };

  return (
    <div className="app-shell">
      <aside className="app-sidebar" aria-label="Основная навигация">
        <div className="brand-row">
          <img className="brand-logo" src="/mira-logo.png" alt="" aria-hidden="true" />
          <div className="brand-copy"><span className="brand-name">Mira</span><span className="brand-caption">Личное рабочее пространство</span></div>
        </div>

        <Link to="/chat" className="new-chat-button" onClick={handleNewChatClick}><Plus className="h-4 w-4" aria-hidden="true" />Новая беседа</Link>

        <nav className="shell-nav">
          <div className="shell-nav-primary">{navLink(HOME)}{navLink(CHAT)}{navLink(NOTIFICATIONS)}{navLink(MAIL)}</div>
          {NAV_GROUPS.map(groupNav)}
        </nav>

        <div className="sidebar-footer"><span className="status-dot" aria-hidden="true" />Локальный режим</div>
      </aside>

      <div className="app-main">
        <div className="app-main-content">{children}</div>

        {moreOpen && (
          <div className="mobile-nav-sheet" role="dialog" aria-label="Все разделы">
            <div className="mobile-nav-sheet-header"><span>Все разделы</span><button type="button" onClick={() => setMoreOpen(false)} aria-label="Закрыть меню"><X className="h-4 w-4" /></button></div>
            <div className="mobile-nav-grid">{mobileMoreContent}</div>
          </div>
        )}

        <nav className="mobile-nav" aria-label="Мобильная навигация">
          {navLink(CHAT, true)}
          {navLink(TASKS, true)}
          {navLink(NOTIFICATIONS, true)}
          <MobileUploadAction />
          <button type="button" onClick={() => setMoreOpen(value => !value)} aria-expanded={moreOpen} aria-label="Открыть все разделы" className="mobile-nav-link mobile-nav-more" data-active={moreOpen || moreActive}>
            {moreOpen ? <X className="shell-nav-icon" aria-hidden="true" /> : <Menu className="shell-nav-icon" aria-hidden="true" />}
            <span>Ещё</span>
          </button>
        </nav>
      </div>
    </div>
  );
}
