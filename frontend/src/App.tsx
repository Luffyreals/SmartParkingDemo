import {
  BarChart3,
  Bell,
  CarFront,
  CreditCard,
  LayoutDashboard,
  LogOut,
  Menu,
  Receipt,
  RefreshCw,
  Settings,
  Wifi,
  WifiOff,
  X,
} from 'lucide-react';
import { useEffect, useRef, useState } from 'react';
import { TicketPrintModal, type PrintableDocument } from './components/TicketPrintModal';
import {
  apiRequest,
  clearAuthSession,
  getStoredToken,
  getStoredUser,
} from './lib/api';
import { AdminPage } from './pages/AdminPage';
import { AnalyticsPage } from './pages/AnalyticsPage';
import { GatePosPage } from './pages/GatePosPage';
import { LoginPage } from './pages/LoginPage';
import { OverviewPage } from './pages/OverviewPage';
import { PassesTariffsPage } from './pages/PassesTariffsPage';
import { TransactionsShiftsPage } from './pages/TransactionsShiftsPage';
import type { AuthUser, OperationalAlerts } from './types';

type PageKey = 'gate' | 'overview' | 'transactions' | 'passes' | 'analytics' | 'admin';

export function App() {
  const [user, setUser] = useState<AuthUser | null>(() => {
    const tok = getStoredToken();
    return tok ? getStoredUser<AuthUser>() : null;
  });
  const [page, setPage] = useState<PageKey>('gate');
  const [mobileMenu, setMobileMenu] = useState(false);
  const [wsConnected, setWsConnected] = useState(false);
  const [refreshSignal, setRefreshSignal] = useState(0);
  const [printDoc, setPrintDoc] = useState<PrintableDocument | null>(null);
  const [toast, setToast] = useState<{ type: 'ok' | 'err'; msg: string } | null>(null);
  const [alerts, setAlerts] = useState<OperationalAlerts | null>(null);
  const [showAlerts, setShowAlerts] = useState(false);
  const toastTimer = useRef<number | null>(null);

  function notify(type: 'ok' | 'err', msg: string) {
    setToast({ type, msg });
    if (toastTimer.current) window.clearTimeout(toastTimer.current);
    toastTimer.current = window.setTimeout(() => setToast(null), 4000);
  }

  useEffect(() => {
    const onExpired = () => {
      setUser(null);
      notify('err', 'Phiên đăng nhập đã hết hạn.');
    };
    window.addEventListener('auth-expired', onExpired);
    return () => window.removeEventListener('auth-expired', onExpired);
  }, []);

  useEffect(() => {
    if (!user) return;
    apiRequest<OperationalAlerts>('/api/alerts')
      .then(setAlerts)
      .catch(() => {});
  }, [user, refreshSignal]);

  useEffect(() => {
    if (!user) return;
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let stopped = false;

    function connect() {
      if (stopped) return;
      const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      ws = new WebSocket(`${proto}//${window.location.host}/ws/live`);
      ws.onopen = () => setWsConnected(true);
      ws.onmessage = () => {
        setRefreshSignal((s) => s + 1);
      };
      ws.onclose = () => {
        setWsConnected(false);
        if (!stopped) {
          reconnectTimer = window.setTimeout(connect, 3000);
        }
      };
      ws.onerror = () => ws?.close();
    }

    connect();
    return () => {
      stopped = true;
      if (reconnectTimer) window.clearTimeout(reconnectTimer);
      ws?.close();
    };
  }, [user]);

  if (!user) {
    return <LoginPage onSuccess={(u) => setUser(u)} />;
  }

  const navItems: Array<{ key: PageKey; label: string; icon: any; roles: string[] }> = [
    { key: 'gate', label: 'Trạm Làn xe (POS)', icon: CarFront, roles: ['ADMIN', 'ACCOUNTANT', 'OPERATOR'] },
    { key: 'overview', label: 'Tổng quan & Sơ đồ', icon: LayoutDashboard, roles: ['ADMIN', 'ACCOUNTANT', 'OPERATOR'] },
    { key: 'transactions', label: 'Giao dịch & Chốt ca', icon: Receipt, roles: ['ADMIN', 'ACCOUNTANT', 'OPERATOR'] },
    { key: 'passes', label: 'Vé tháng & Bảng giá', icon: CreditCard, roles: ['ADMIN', 'ACCOUNTANT', 'OPERATOR'] },
    { key: 'analytics', label: 'Thống kê doanh thu', icon: BarChart3, roles: ['ADMIN', 'ACCOUNTANT'] },
    { key: 'admin', label: 'Quản trị & Nhật ký', icon: Settings, roles: ['ADMIN', 'ACCOUNTANT', 'OPERATOR'] },
  ];

  const visibleNav = navItems.filter((item) => item.roles.includes(user.role));
  const alertCount =
    (alerts?.overdue_turns.length || 0) +
    (alerts?.expiring_passes.length || 0) +
    (alerts?.lost_cards.length || 0);

  function handleLogout() {
    clearAuthSession();
    setUser(null);
  }

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900">
      {/* Sidebar Desktop */}
      <aside className="hidden lg:flex w-64 flex-col border-r border-slate-200 bg-white shrink-0">
        <div className="flex items-center gap-3 px-5 py-5 border-b border-slate-100">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600 text-white shadow-xs">
            <CarFront className="h-5 w-5" />
          </div>
          <div>
            <div className="font-extrabold text-sm tracking-tight text-slate-900">Smart Parking</div>
            <div className="text-[11px] text-slate-500">PTIT Production v2.0</div>
          </div>
        </div>

        <nav className="flex-1 p-3 space-y-1">
          {visibleNav.map((item) => {
            const Icon = item.icon;
            const active = page === item.key;
            return (
              <button
                key={item.key}
                onClick={() => setPage(item.key)}
                className={`w-full flex items-center gap-3 rounded-xl px-3.5 py-2.5 text-sm font-semibold transition ${
                  active
                    ? 'bg-indigo-50 text-indigo-700'
                    : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                }`}
              >
                <Icon className="h-4 w-4 shrink-0" />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>

        <div className="border-t border-slate-100 p-4 space-y-3">
          <div className="rounded-xl bg-slate-50 p-3 border border-slate-200/70">
            <div className="text-xs font-bold text-slate-900 truncate">{user.full_name}</div>
            <div className="mt-0.5 flex items-center justify-between text-[11px] text-slate-500">
              <span className="font-mono-plate">{user.username}</span>
              <span className="rounded-md bg-indigo-100 px-1.5 py-0.5 font-bold text-indigo-700">
                {user.role}
              </span>
            </div>
          </div>
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 rounded-xl border border-slate-200 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
          >
            <LogOut className="h-3.5 w-3.5" />
            Đăng xuất
          </button>
        </div>
      </aside>

      {/* Mobile Drawer */}
      {mobileMenu && (
        <div className="fixed inset-0 z-50 lg:hidden flex">
          <div className="fixed inset-0 bg-slate-900/50" onClick={() => setMobileMenu(false)} />
          <div className="relative z-10 w-64 bg-white h-full flex flex-col p-4 space-y-2">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <span className="font-bold">Smart Parking PTIT</span>
              <button onClick={() => setMobileMenu(false)}>
                <X className="h-5 w-5" />
              </button>
            </div>
            {visibleNav.map((item) => {
              const Icon = item.icon;
              return (
                <button
                  key={item.key}
                  onClick={() => {
                    setPage(item.key);
                    setMobileMenu(false);
                  }}
                  className={`w-full flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold ${
                    page === item.key ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
            <button
              onClick={handleLogout}
              className="mt-auto w-full flex items-center justify-center gap-2 rounded-xl border border-slate-200 py-2 text-xs font-semibold"
            >
              <LogOut className="h-3.5 w-3.5" />
              Đăng xuất
            </button>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="sticky top-0 z-30 flex items-center justify-between border-b border-slate-200 bg-white/90 backdrop-blur-sm px-4 sm:px-6 py-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setMobileMenu(true)}
              className="lg:hidden rounded-lg border border-slate-200 p-2 text-slate-600"
            >
              <Menu className="h-4 w-4" />
            </button>
            <div
              className={`inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-semibold ${
                wsConnected
                  ? 'bg-emerald-50 text-emerald-700'
                  : 'bg-amber-50 text-amber-700'
              }`}
            >
              {wsConnected ? <Wifi className="h-3.5 w-3.5" /> : <WifiOff className="h-3.5 w-3.5" />}
              <span>{wsConnected ? 'Đồng bộ Real-time' : 'Đang kết nối lại...'}</span>
            </div>
          </div>

          <div className="flex items-center gap-2.5 relative">
            <button
              onClick={() => setShowAlerts((v) => !v)}
              className="relative rounded-xl border border-slate-200 bg-white p-2 text-slate-600 hover:bg-slate-50"
              title="Cảnh báo vận hành"
            >
              <Bell className="h-4 w-4" />
              {alertCount > 0 && (
                <span className="absolute -top-1 -right-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-rose-600 px-1 text-[10px] font-bold text-white">
                  {alertCount}
                </span>
              )}
            </button>
            <button
              onClick={() => setRefreshSignal((s) => s + 1)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <RefreshCw className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Làm mới</span>
            </button>

            {showAlerts && alerts && (
              <div className="absolute right-0 top-12 w-80 rounded-2xl border border-slate-200 bg-white p-4 shadow-xl space-y-3 z-50">
                <div className="flex items-center justify-between font-bold text-sm text-slate-900">
                  <span>Cảnh báo vận hành</span>
                  <button onClick={() => setShowAlerts(false)} className="text-xs text-slate-400">
                    Đóng
                  </button>
                </div>
                <div className="space-y-2 text-xs max-h-72 overflow-y-auto">
                  <div className="font-semibold text-amber-700">
                    Xe gửi quá 24h ({alerts.overdue_turns.length})
                  </div>
                  {alerts.overdue_turns.slice(0, 5).map((o) => (
                    <div key={o.id} className="rounded-lg bg-amber-50 p-2 text-amber-900">
                      <strong className="font-mono-plate">{o.bienso}</strong> · {o.hours_parked}h ({o.tenbaido})
                    </div>
                  ))}
                  <div className="font-semibold text-indigo-700 pt-1">
                    Vé tháng sắp hết hạn ({alerts.expiring_passes.length})
                  </div>
                  {alerts.expiring_passes.slice(0, 5).map((p) => (
                    <div key={p.id} className="rounded-lg bg-indigo-50 p-2 text-indigo-900">
                      <strong className="font-mono-plate">{p.bienso}</strong> · còn {p.days_left} ngày ({p.ten_khachhang})
                    </div>
                  ))}
                  <div className="font-semibold text-rose-700 pt-1">
                    Thẻ đang khóa / báo mất ({alerts.lost_cards.length})
                  </div>
                </div>
              </div>
            )}
          </div>
        </header>

        <main className="flex-1 p-4 sm:p-6 lg:p-8 max-w-[1600px] w-full mx-auto">
          {page === 'gate' && (
            <GatePosPage
              user={user}
              refreshSignal={refreshSignal}
              onNotify={notify}
              onPrint={setPrintDoc}
            />
          )}
          {page === 'overview' && (
            <OverviewPage user={user} refreshSignal={refreshSignal} onNotify={notify} />
          )}
          {page === 'transactions' && (
            <TransactionsShiftsPage
              user={user}
              refreshSignal={refreshSignal}
              onNotify={notify}
              onPrint={setPrintDoc}
            />
          )}
          {page === 'passes' && (
            <PassesTariffsPage
              user={user}
              refreshSignal={refreshSignal}
              onNotify={notify}
              onPrint={setPrintDoc}
            />
          )}
          {page === 'analytics' && (
            <AnalyticsPage refreshSignal={refreshSignal} onNotify={notify} />
          )}
          {page === 'admin' && (
            <AdminPage user={user} refreshSignal={refreshSignal} onNotify={notify} />
          )}
        </main>
      </div>

      {/* Global Toast */}
      {toast && (
        <div
          className={`fixed bottom-5 right-5 z-50 rounded-xl px-4 py-3 text-sm font-semibold shadow-lg border ${
            toast.type === 'ok'
              ? 'bg-emerald-600 text-white border-emerald-700'
              : 'bg-rose-600 text-white border-rose-700'
          }`}
        >
          {toast.msg}
        </div>
      )}

      {/* Print Modal */}
      <TicketPrintModal doc={printDoc} onClose={() => setPrintDoc(null)} />
    </div>
  );
}

export default App;
