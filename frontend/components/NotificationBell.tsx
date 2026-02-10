import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Bell, Check, ExternalLink } from 'lucide-react';
import { useAuthFetch } from '../store/AuthContext';

type NotificationType = 'ALERT' | 'WARNING' | 'INFO';

type NotificationItem = {
  id: string;
  type: NotificationType;
  product?: string | null;
  message: string;
  severity: number;
  created_at: string;
  read: boolean;
  meta?: any;
};

type NotificationsResponse = {
  ok: boolean;
  badge_count?: number;
  unread_risk_count?: number;
  unread_count: number;
  count: number;
  items: NotificationItem[];
};

type Props = {
  onNavigate: (page: string) => void;
  currentPage: string;
};

const typePill = (t: NotificationType) => {
  switch (t) {
    case 'ALERT':
      return 'bg-red-100 text-red-700 dark:bg-red-950/30 dark:text-red-300';
    case 'WARNING':
      return 'bg-amber-100 text-amber-800 dark:bg-amber-950/30 dark:text-amber-300';
    default:
      return 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-200';
  }
};

export const NotificationBell: React.FC<Props> = ({ onNavigate, currentPage }) => {
  const authFetch = useAuthFetch();
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);

  const containerRef = useRef<HTMLDivElement | null>(null);

  const load = async () => {
    setIsLoading(true);
    try {
      const res = await authFetch('/notifications?include_info=true&info_scope=UNKNOWN&limit=50', { cache: 'no-store' });
      if (!res.ok) {
        const text = await res.text();
        console.error('[NotificationBell] /notifications failed', { status: res.status, body: text?.slice(0, 300) });
        setItems([]);
        setUnreadCount(0);
        return;
      }
      const payload = (await res.json()) as NotificationsResponse;
      setItems(payload.items || []);
      // UX: badge is ALERT+WARNING unread (single source of truth from backend)
      const badge = Number(payload.badge_count ?? payload.unread_risk_count ?? payload.unread_count ?? 0);
      setUnreadCount(Number.isFinite(badge) ? badge : 0);
    } catch {
      setItems([]);
      setUnreadCount(0);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    let cancelled = false;

    const onInventoryChanged = () => {
      if (!cancelled) load();
    };

    const onDocMouseDown = (e: MouseEvent) => {
      if (!open) return;
      const el = containerRef.current;
      if (!el) return;
      if (!el.contains(e.target as any)) setOpen(false);
    };

    load();
    window.addEventListener('inventory:changed', onInventoryChanged);
    document.addEventListener('mousedown', onDocMouseDown);
    const intervalId = window.setInterval(load, 30000);

    return () => {
      cancelled = true;
      window.removeEventListener('inventory:changed', onInventoryChanged);
      document.removeEventListener('mousedown', onDocMouseDown);
      window.clearInterval(intervalId);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const sorted = useMemo(() => {
    return [...items].sort((a, b) => {
      if (Number(a.read) !== Number(b.read)) return a.read ? 1 : -1;
      return (b.severity || 1) - (a.severity || 1);
    });
  }, [items]);

  const markRead = async (ids: string[]) => {
    if (!ids.length) return;
    try {
      await authFetch('/notifications/mark-read', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids }),
      });
    } catch {
      // best-effort
    }
  };

  const viewNotification = async (n: NotificationItem) => {
    await markRead([n.id]);
    await load();

    // User chooses what to open: clicking View navigates.
    if (currentPage !== 'inventory') {
      onNavigate('inventory');
    }

    // Focus the inventory UI without forcing redirects elsewhere.
    const product = String(n.product || n.meta?.product_name || '').trim();
    const status = String(n.meta?.status || n.type || '').toUpperCase();

    window.setTimeout(() => {
      window.dispatchEvent(
        new CustomEvent('inventory:focus', {
          detail: {
            product,
            status,
          },
        })
      );
    }, 50);
  };

  const markAllRead = async () => {
    const unread = items.filter((x) => !x.read).map((x) => x.id);
    await markRead(unread);
    await load();
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        onClick={() => setOpen((v) => !v)}
        className="p-2 text-text-secondary hover:bg-slate-100 dark:hover:bg-slate-800 rounded-lg relative"
        aria-label="Open notifications"
        type="button"
      >
        <Bell size={20} />
        {unreadCount > 0 && (
          <span className="absolute -top-1 -right-1 min-w-5 h-5 px-1.5 bg-error text-white text-[11px] leading-5 rounded-full text-center font-semibold">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-[360px] max-w-[90vw] bg-card-light dark:bg-card-dark border border-slate-200 dark:border-slate-800 rounded-2xl shadow-lg overflow-hidden z-50">
          <div className="px-4 py-3 flex items-center justify-between">
            <div>
              <p className="text-sm font-semibold">Notifications</p>
              <p className="text-xs text-text-secondary dark:text-text-secondaryDark">
                {unreadCount} unread
              </p>
            </div>
            <button
              onClick={markAllRead}
              className="text-xs px-2 py-1 rounded-lg bg-slate-100 hover:bg-slate-200 dark:bg-slate-800 dark:hover:bg-slate-700"
              type="button"
              disabled={items.every((x) => x.read)}
              title="Mark all as read"
            >
              <span className="inline-flex items-center gap-1">
                <Check size={14} /> Mark all
              </span>
            </button>
          </div>

          <div className="max-h-[420px] overflow-auto">
            {isLoading && (
              <div className="px-4 py-6 text-sm text-text-secondary dark:text-text-secondaryDark">Loading…</div>
            )}

            {!isLoading && sorted.length === 0 && (
              <div className="px-4 py-6 text-sm text-text-secondary dark:text-text-secondaryDark">
                No notifications right now.
              </div>
            )}

            {!isLoading && sorted.map((n) => (
              <div
                key={n.id}
                className={`px-4 py-3 border-t border-slate-200 dark:border-slate-800 ${n.read ? 'opacity-70' : ''}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className={`text-[11px] px-2 py-0.5 rounded-full font-semibold ${typePill(n.type)}`}>{n.type}</span>
                      {n.product && (
                        <span className="text-xs font-semibold truncate">{n.product}</span>
                      )}
                      {!n.read && <span className="text-[10px] px-2 py-0.5 rounded-full bg-primary/10 text-primary font-semibold">NEW</span>}
                    </div>
                    <p className="text-sm text-text-secondary dark:text-text-secondaryDark leading-snug">
                      {n.message}
                    </p>
                  </div>

                  <button
                    onClick={() => viewNotification(n)}
                    className="shrink-0 inline-flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg bg-primary text-white hover:opacity-90"
                    type="button"
                  >
                    <ExternalLink size={14} /> View
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
