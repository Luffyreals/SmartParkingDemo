import {
  Building2,
  Car,
  CreditCard,
  History,
  KeyRound,
  Plus,
  Shield,
  Users,
} from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';
import { apiRequest, formatDateTime, formatVnd } from '../lib/api';
import type { AuditLog, AuthUser, ParkingLot, ZoneSummary } from '../types';

interface AdminPageProps {
  user: AuthUser;
  refreshSignal: number;
  onNotify: (type: 'ok' | 'err', msg: string) => void;
}

export function AdminPage({ user, refreshSignal, onNotify }: AdminPageProps) {
  const [tab, setTab] = useState<'accounts' | 'people' | 'cards' | 'infra' | 'audit'>(
    user.role === 'ADMIN' ? 'accounts' : 'people',
  );
  const [accounts, setAccounts] = useState<any[]>([]);
  const [employees, setEmployees] = useState<any[]>([]);
  const [customers, setCustomers] = useState<any[]>([]);
  const [walkins, setWalkins] = useState<any[]>([]);
  const [vehicles, setVehicles] = useState<any[]>([]);
  const [cards, setCards] = useState<any[]>([]);
  const [lots, setLots] = useState<ParkingLot[]>([]);
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>([]);

  // Create card
  const [newCardCode, setNewCardCode] = useState('');
  // Create account
  const [accEmpId, setAccEmpId] = useState<number | ''>('');
  const [accUsername, setAccUsername] = useState('');
  const [accPassword, setAccPassword] = useState('');
  const [accRole, setAccRole] = useState('OPERATOR');
  // Add slots
  const [slotZoneId, setSlotZoneId] = useState<number | ''>('');
  const [slotCount, setSlotCount] = useState(5);

  async function loadAll() {
    try {
      const requests: Promise<any>[] = [
        apiRequest<any[]>('/api/cards?detail=true'),
        apiRequest<ParkingLot[]>('/api/lots'),
        apiRequest<ZoneSummary[]>('/api/zones'),
        apiRequest<any[]>('/api/people/employees'),
        apiRequest<any[]>('/api/people/customers'),
        apiRequest<any[]>('/api/people/walkins?limit=100'),
        apiRequest<any[]>('/api/vehicles'),
      ];
      if (user.role === 'ADMIN') {
        requests.push(apiRequest<any[]>('/api/accounts'));
      }
      if (user.role === 'ADMIN' || user.role === 'ACCOUNTANT') {
        requests.push(apiRequest<AuditLog[]>('/api/audit-logs?limit=100'));
      }
      const results = await Promise.all(requests);
      setCards(results[0]);
      setLots(results[1]);
      setZones(results[2]);
      setEmployees(results[3]);
      setCustomers(results[4]);
      setWalkins(results[5]);
      setVehicles(results[6]);
      if (results[2][0] && !slotZoneId) setSlotZoneId(results[2][0].id);
      let idx = 7;
      if (user.role === 'ADMIN') {
        setAccounts(results[idx++]);
      }
      if (user.role === 'ADMIN' || user.role === 'ACCOUNTANT') {
        setAuditLogs(results[idx++]);
      }
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  useEffect(() => {
    loadAll();
  }, [refreshSignal]);

  async function handleCreateCard(e: FormEvent) {
    e.preventDefault();
    try {
      await apiRequest('/api/cards', {
        method: 'POST',
        body: JSON.stringify({ code: newCardCode.trim() }),
      });
      onNotify('ok', `Đã thêm thẻ ${newCardCode.trim()}.`);
      setNewCardCode('');
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleCardStatus(cardId: number, status: number) {
    try {
      await apiRequest(`/api/cards/${cardId}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      onNotify('ok', 'Đã cập nhật trạng thái thẻ.');
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleCreateAccount(e: FormEvent) {
    e.preventDefault();
    if (!accEmpId) return;
    try {
      await apiRequest('/api/accounts', {
        method: 'POST',
        body: JSON.stringify({
          employee_id: Number(accEmpId),
          username: accUsername,
          password: accPassword,
          role: accRole,
        }),
      });
      onNotify('ok', `Đã tạo tài khoản ${accUsername}.`);
      setAccUsername('');
      setAccPassword('');
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function toggleAccountActive(acc: any) {
    try {
      await apiRequest(`/api/accounts/${acc.id}`, {
        method: 'PATCH',
        body: JSON.stringify({ is_active: !acc.is_active }),
      });
      onNotify('ok', `Đã ${acc.is_active ? 'khóa' : 'mở khóa'} tài khoản ${acc.username}.`);
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleAddSlots(e: FormEvent) {
    e.preventDefault();
    if (!slotZoneId) return;
    try {
      const res = await apiRequest<{ created: number }>('/api/slots', {
        method: 'POST',
        body: JSON.stringify({ zone_id: Number(slotZoneId), count: Number(slotCount) }),
      });
      onNotify('ok', `Đã thêm ${res.created} vị trí đỗ mới.`);
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  const employeesWithoutAccount = employees.filter(
    (emp) => !accounts.some((a) => a.idnv === emp.id),
  );

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Quản trị &amp; Danh bạ Hệ thống
          </h1>
          <p className="text-sm text-slate-500">
            Quản lý tài khoản RBAC, nhân sự, khách hàng, phương tiện, kho thẻ RFID và audit logs.
          </p>
        </div>

        <div className="inline-flex flex-wrap rounded-xl border border-slate-200 bg-white p-1 gap-1">
          {user.role === 'ADMIN' && (
            <button
              onClick={() => setTab('accounts')}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
                tab === 'accounts' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Shield className="h-3.5 w-3.5" />
              Tài khoản RBAC
            </button>
          )}
          <button
            onClick={() => setTab('people')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
              tab === 'people' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Users className="h-3.5 w-3.5" />
            Nhân sự &amp; Khách xe
          </button>
          <button
            onClick={() => setTab('cards')}
            className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
              tab === 'cards' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <CreditCard className="h-3.5 w-3.5" />
            Kho thẻ RFID ({cards.length})
          </button>
          {user.role === 'ADMIN' && (
            <button
              onClick={() => setTab('infra')}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
                tab === 'infra' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <Building2 className="h-3.5 w-3.5" />
              Hạ tầng Bãi đỗ
            </button>
          )}
          {(user.role === 'ADMIN' || user.role === 'ACCOUNTANT') && (
            <button
              onClick={() => setTab('audit')}
              className={`inline-flex items-center gap-1.5 rounded-lg px-3.5 py-2 text-xs font-semibold ${
                tab === 'audit' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
              }`}
            >
              <History className="h-3.5 w-3.5" />
              Audit Logs
            </button>
          )}
        </div>
      </div>

      {tab === 'accounts' && user.role === 'ADMIN' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
            <div className="flex items-center gap-2 font-bold text-slate-900">
              <KeyRound className="h-4 w-4 text-indigo-600" />
              <span>Cấp tài khoản mới</span>
            </div>
            <form onSubmit={handleCreateAccount} className="space-y-3">
              <select
                value={accEmpId}
                onChange={(e) => setAccEmpId(Number(e.target.value))}
                required
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="">-- Chọn nhân viên chưa có TK --</option>
                {employeesWithoutAccount.map((e) => (
                  <option key={e.id} value={e.id}>
                    {e.hoten} ({e.chucvu})
                  </option>
                ))}
              </select>
              <input
                type="text"
                required
                placeholder="Tên đăng nhập"
                value={accUsername}
                onChange={(e) => setAccUsername(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              />
              <input
                type="password"
                required
                placeholder="Mật khẩu (>= 6 ký tự)"
                value={accPassword}
                onChange={(e) => setAccPassword(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              />
              <select
                value={accRole}
                onChange={(e) => setAccRole(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                <option value="OPERATOR">OPERATOR (Bảo vệ trực cổng)</option>
                <option value="ACCOUNTANT">ACCOUNTANT (Thu ngân / Kế toán)</option>
                <option value="ADMIN">ADMIN (Quản trị toàn quyền)</option>
              </select>
              <button
                type="submit"
                className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white hover:bg-indigo-700"
              >
                Tạo tài khoản
              </button>
            </form>
          </div>

          <div className="lg:col-span-8 rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <div className="border-b border-slate-200 px-5 py-4 flex items-center gap-2 font-bold text-slate-900">
              <Users className="h-4 w-4 text-indigo-600" />
              <span>Danh sách tài khoản ({accounts.length})</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Tài khoản</th>
                    <th className="px-4 py-3">Nhân viên</th>
                    <th className="px-4 py-3">Vai trò</th>
                    <th className="px-4 py-3">Đăng nhập gần nhất</th>
                    <th className="px-4 py-3 text-right">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {accounts.map((a) => (
                    <tr key={a.id}>
                      <td className="px-4 py-3 font-mono-plate font-bold">{a.username}</td>
                      <td className="px-4 py-3">
                        <div className="font-medium text-slate-900">{a.ten_nhanvien}</div>
                        <div className="text-xs text-slate-500">{a.chucvu}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700">
                          {a.role}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        {formatDateTime(a.last_login_at)}
                      </td>
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={() => toggleAccountActive(a)}
                          className={`rounded-lg px-2.5 py-1 text-xs font-semibold ${
                            a.is_active
                              ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
                              : 'bg-rose-50 text-rose-700 hover:bg-rose-100'
                          }`}
                        >
                          {a.is_active ? 'Đang hoạt động' : 'Đã khóa'}
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {tab === 'people' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Employees */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
              <div className="border-b border-slate-200 px-5 py-4 font-bold text-slate-900">
                Nhân sự vận hành ({employees.length})
              </div>
              <div className="overflow-x-auto max-h-80">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 font-semibold uppercase text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5">Họ tên</th>
                      <th className="px-4 py-2.5">Chức vụ</th>
                      <th className="px-4 py-2.5">Bãi trực</th>
                      <th className="px-4 py-2.5">SĐT</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {employees.map((e) => (
                      <tr key={e.id}>
                        <td className="px-4 py-2.5 font-semibold text-slate-900">{e.hoten}</td>
                        <td className="px-4 py-2.5">{e.chucvu}</td>
                        <td className="px-4 py-2.5 text-slate-600">{e.tenbaido || 'Tất cả'}</td>
                        <td className="px-4 py-2.5 font-mono-plate">{e.sdt}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Customers */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
              <div className="border-b border-slate-200 px-5 py-4 font-bold text-slate-900">
                Khách hàng đăng ký vé tháng ({customers.length})
              </div>
              <div className="overflow-x-auto max-h-80">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 font-semibold uppercase text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5">Họ tên</th>
                      <th className="px-4 py-2.5">Đối tượng</th>
                      <th className="px-4 py-2.5">Biển số ĐK</th>
                      <th className="px-4 py-2.5 text-right">Vé hiệu lực</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {customers.map((c) => (
                      <tr key={c.id}>
                        <td className="px-4 py-2.5">
                          <div className="font-semibold text-slate-900">{c.hoten}</div>
                          <div className="text-slate-500">{c.sdt}</div>
                        </td>
                        <td className="px-4 py-2.5">{c.loaikhachhang}</td>
                        <td className="px-4 py-2.5 font-mono-plate">{c.bien_so_dang_ky || '—'}</td>
                        <td className="px-4 py-2.5 text-right font-bold text-indigo-700">
                          {c.so_ve_hieu_luc}/{c.tong_ve_da_dang_ky}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Vehicles */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
              <div className="border-b border-slate-200 px-5 py-4 flex items-center gap-2 font-bold text-slate-900">
                <Car className="h-4 w-4 text-indigo-600" />
                <span>Danh bạ phương tiện ({vehicles.length})</span>
              </div>
              <div className="overflow-x-auto max-h-80">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 font-semibold uppercase text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5">Biển số</th>
                      <th className="px-4 py-2.5">Loại xe</th>
                      <th className="px-4 py-2.5">Chủ xe</th>
                      <th className="px-4 py-2.5 text-right">Lượt gửi</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {vehicles.map((v) => (
                      <tr key={v.id}>
                        <td className="px-4 py-2.5 font-mono-plate font-bold text-slate-900">{v.bienso}</td>
                        <td className="px-4 py-2.5">{v.loaiphuongtien}</td>
                        <td className="px-4 py-2.5 text-slate-600">{v.chu_xe}</td>
                        <td className="px-4 py-2.5 text-right font-semibold">{v.tong_luot}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Walk-in visitors */}
            <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
              <div className="border-b border-slate-200 px-5 py-4 font-bold text-slate-900">
                Lượt khách vãng lai gần đây ({walkins.length})
              </div>
              <div className="overflow-x-auto max-h-80">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 font-semibold uppercase text-slate-500 border-b border-slate-200">
                    <tr>
                      <th className="px-4 py-2.5">Biển số</th>
                      <th className="px-4 py-2.5">Vị trí / Thẻ</th>
                      <th className="px-4 py-2.5">Trạng thái</th>
                      <th className="px-4 py-2.5 text-right">Phí</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {walkins.map((w) => (
                      <tr key={w.id_luotdo}>
                        <td className="px-4 py-2.5">
                          <div className="font-mono-plate font-bold text-slate-900">{w.bienso}</div>
                          <div className="text-slate-500">{w.loaiphuongtien}</div>
                        </td>
                        <td className="px-4 py-2.5 text-slate-600">
                          {w.vitri_do} · Thẻ {w.mathe}
                        </td>
                        <td className="px-4 py-2.5">{w.trang_thai}</td>
                        <td className="px-4 py-2.5 text-right font-semibold">
                          {w.chiphi !== null ? formatVnd(w.chiphi) : '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      )}

      {tab === 'cards' && (
        <div className="space-y-4">
          <form
            onSubmit={handleCreateCard}
            className="flex flex-wrap items-center gap-3 rounded-2xl border border-slate-200 bg-white p-4 shadow-xs"
          >
            <input
              type="text"
              required
              placeholder="Nhập mã thẻ RFID mới (VD: 016)"
              value={newCardCode}
              onChange={(e) => setNewCardCode(e.target.value)}
              className="rounded-xl border border-slate-200 px-3.5 py-2 text-sm font-mono-plate"
            />
            <button
              type="submit"
              className="inline-flex items-center gap-1.5 rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
            >
              <Plus className="h-4 w-4" />
              Thêm thẻ mới
            </button>
          </form>

          <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Mã thẻ</th>
                  <th className="px-4 py-3">Tình trạng</th>
                  <th className="px-4 py-3">Gắn với xe / vé</th>
                  <th className="px-4 py-3 text-right">Thao tác</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {cards.map((c) => (
                  <tr key={c.id}>
                    <td className="px-4 py-3 font-mono-plate font-bold">{c.maso}</td>
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                          c.trangthai === 1
                            ? 'bg-emerald-50 text-emerald-700'
                            : c.trangthai === 0
                              ? 'bg-indigo-50 text-indigo-700'
                              : 'bg-rose-50 text-rose-700'
                        }`}
                      >
                        {c.trangthai === 1 ? 'Sẵn sàng' : c.trangthai === 0 ? 'Đang dùng' : 'Báo mất / Khóa'}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-600">
                      {c.bienso_dang_gui
                        ? `Đang gửi: ${c.bienso_dang_gui} (${c.tenbaido} · ${c.khuvuc}-${c.sothutu})`
                        : c.bienso_ve_thang
                          ? `Vé tháng: ${c.bienso_ve_thang} (${c.chu_ve_thang})`
                          : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      {c.trangthai !== 0 && (
                        <button
                          onClick={() => handleCardStatus(c.id, c.trangthai === 2 ? 1 : 2)}
                          className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold hover:bg-slate-50"
                        >
                          {c.trangthai === 2 ? 'Mở khóa thẻ' : 'Khóa / Báo mất'}
                        </button>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {tab === 'infra' && user.role === 'ADMIN' && (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
            <h2 className="font-bold text-slate-900">Mở rộng ô đỗ cho khu vực</h2>
            <form onSubmit={handleAddSlots} className="space-y-3">
              <select
                value={slotZoneId}
                onChange={(e) => setSlotZoneId(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
              >
                {zones.map((z) => (
                  <option key={z.id} value={z.id}>
                    {z.tenbaido} · Khu {z.ten} (hiện có {z.tong_cho} ô)
                  </option>
                ))}
              </select>
              <input
                type="number"
                min={1}
                max={50}
                value={slotCount}
                onChange={(e) => setSlotCount(Number(e.target.value))}
                className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
              />
              <button
                type="submit"
                className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white hover:bg-indigo-700"
              >
                Thêm vị trí đỗ
              </button>
            </form>
          </div>
          <div className="lg:col-span-7 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-3">
            <h2 className="font-bold text-slate-900">Danh sách bãi đỗ &amp; công suất</h2>
            {lots.map((l) => (
              <div key={l.id} className="rounded-xl border border-slate-200 p-3.5 flex justify-between">
                <div>
                  <div className="font-semibold text-slate-900">{l.tenbaido}</div>
                  <div className="text-xs text-slate-500">{l.diadiem}</div>
                </div>
                <div className="text-xs font-semibold text-slate-700">
                  {l.tong_cho} ô ({l.cho_trong} trống)
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {tab === 'audit' && (
        <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          <div className="border-b border-slate-200 px-5 py-4 font-bold text-slate-900">
            Nhật ký thao tác hệ thống (100 bản ghi gần nhất)
          </div>
          <div className="overflow-x-auto max-h-[520px]">
            <table className="w-full text-left text-xs">
              <thead className="sticky top-0 bg-slate-50 font-semibold uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Thời gian</th>
                  <th className="px-4 py-3">Người thực hiện</th>
                  <th className="px-4 py-3">Hành động</th>
                  <th className="px-4 py-3">Đối tượng</th>
                  <th className="px-4 py-3">Chi tiết</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {auditLogs.map((log) => (
                  <tr key={log.id} className="hover:bg-slate-50">
                    <td className="px-4 py-2.5 text-slate-500 whitespace-nowrap">
                      {formatDateTime(log.created_at)}
                    </td>
                    <td className="px-4 py-2.5 font-mono-plate font-semibold text-slate-800">
                      {log.actor_username}
                    </td>
                    <td className="px-4 py-2.5">
                      <span className="rounded-md bg-slate-100 px-2 py-0.5 font-mono-plate font-semibold text-slate-800">
                        {log.action}
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-slate-600">
                      {log.entity_type} {log.entity_id ? `#${log.entity_id}` : ''}
                    </td>
                    <td className="px-4 py-2.5 font-mono-plate text-slate-500 max-w-md truncate">
                      {log.details_json}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
