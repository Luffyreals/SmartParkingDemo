import { Clock, Download, Printer, Receipt, Search, Wallet } from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';
import type { PrintableDocument } from '../components/TicketPrintModal';
import { apiRequest, formatDateTime, formatVnd } from '../lib/api';
import type { AuthUser, ShiftRecord, TransactionRecord } from '../types';

interface TransactionsShiftsPageProps {
  user: AuthUser;
  refreshSignal: number;
  onNotify: (type: 'ok' | 'err', msg: string) => void;
  onPrint: (doc: PrintableDocument) => void;
}

export function TransactionsShiftsPage({
  user,
  refreshSignal,
  onNotify,
  onPrint,
}: TransactionsShiftsPageProps) {
  const [tab, setTab] = useState<'tx' | 'shifts'>('tx');
  const [transactions, setTransactions] = useState<TransactionRecord[]>([]);
  const [keyword, setKeyword] = useState('');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  // Shifts
  const [activeShift, setActiveShift] = useState<ShiftRecord | null>(null);
  const [shifts, setShifts] = useState<ShiftRecord[]>([]);
  const [openingCash, setOpeningCash] = useState(500000);
  const [actualCash, setActualCash] = useState(500000);
  const [shiftNote, setShiftNote] = useState('');

  async function loadTransactions() {
    const params = new URLSearchParams();
    if (keyword.trim()) params.set('keyword', keyword.trim());
    if (startDate) params.set('start_date', startDate);
    if (endDate) params.set('end_date', endDate);
    const data = await apiRequest<TransactionRecord[]>(`/api/transactions?${params.toString()}`);
    setTransactions(data);
  }

  async function loadShifts() {
    const [activeRes, listRes] = await Promise.all([
      apiRequest<{ shift: ShiftRecord | null }>('/api/shifts/active'),
      apiRequest<ShiftRecord[]>('/api/shifts'),
    ]);
    setActiveShift(activeRes.shift);
    setShifts(listRes);
    if (activeRes.shift?.live_expected_cash !== undefined) {
      setActualCash(activeRes.shift.live_expected_cash);
    }
  }

  async function loadAll() {
    try {
      await Promise.all([loadTransactions(), loadShifts()]);
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  useEffect(() => {
    loadAll();
  }, [refreshSignal]);

  function exportCsv() {
    const headers = ['ID', 'Thời gian', 'Hình thức', 'Biển số', 'Thẻ', 'Vị trí', 'Số tiền', 'Trạng thái', 'Nhân viên'];
    const rows = transactions.map((t) => [
      t.ma_gd,
      t.giothanhtoan,
      t.hinhthuc,
      t.bienso || '',
      t.mathe || '',
      t.vitri || '',
      t.chiphi,
      t.trangthai,
      t.nhanvien,
    ]);
    const csv = '\uFEFF' + [headers, ...rows].map((r) => r.map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `giao-dich-bai-xe-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async function handleStatusChange(id: number, status: string) {
    try {
      await apiRequest(`/api/transactions/${id}/status`, {
        method: 'PATCH',
        body: JSON.stringify({ status }),
      });
      onNotify('ok', `Đã cập nhật giao dịch #${id} sang "${status}".`);
      await loadTransactions();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleOpenShift(e: FormEvent) {
    e.preventDefault();
    try {
      await apiRequest('/api/shifts/open', {
        method: 'POST',
        body: JSON.stringify({ opening_cash: Number(openingCash), note: shiftNote }),
      });
      onNotify('ok', 'Đã mở ca làm việc mới.');
      setShiftNote('');
      await loadShifts();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleCloseShift(e: FormEvent) {
    e.preventDefault();
    if (!activeShift) return;
    try {
      const res = await apiRequest<{ expected_cash: number; actual_cash: number; diff: number }>(
        `/api/shifts/${activeShift.id}/close`,
        {
          method: 'POST',
          body: JSON.stringify({ actual_cash: Number(actualCash), note: shiftNote }),
        },
      );
      onNotify(
        'ok',
        `Đã chốt ca #${activeShift.id}. Chênh lệch tiền mặt: ${formatVnd(res.diff)}.`,
      );
      setShiftNote('');
      await loadShifts();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Giao dịch &amp; Chốt ca Thu ngân
          </h1>
          <p className="text-sm text-slate-500">
            Tra cứu biên lai, xuất báo cáo CSV và đối soát tiền mặt/chuyển khoản theo ca trực.
          </p>
        </div>
        <div className="inline-flex rounded-xl border border-slate-200 bg-white p-1">
          <button
            onClick={() => setTab('tx')}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              tab === 'tx' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Receipt className="h-3.5 w-3.5" />
            Lịch sử giao dịch
          </button>
          <button
            onClick={() => setTab('shifts')}
            className={`inline-flex items-center gap-2 rounded-lg px-4 py-2 text-xs font-semibold transition ${
              tab === 'shifts' ? 'bg-indigo-600 text-white' : 'text-slate-600 hover:bg-slate-50'
            }`}
          >
            <Wallet className="h-3.5 w-3.5" />
            Chốt ca làm việc
          </button>
        </div>
      </div>

      {tab === 'tx' ? (
        <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 p-4">
            <div className="flex flex-wrap items-center gap-2.5">
              <div className="relative">
                <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  value={keyword}
                  onChange={(e) => setKeyword(e.target.value)}
                  placeholder="Biển số, mã thẻ, nhân viên..."
                  className="rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 py-2 text-sm"
                />
              </div>
              <input
                type="date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              />
              <input
                type="date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm"
              />
              <button
                onClick={loadTransactions}
                className="rounded-xl bg-slate-900 px-4 py-2 text-sm font-semibold text-white hover:bg-slate-800"
              >
                Lọc
              </button>
            </div>
            <button
              onClick={exportCsv}
              className="inline-flex items-center gap-2 rounded-xl border border-slate-200 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50"
            >
              <Download className="h-3.5 w-3.5" />
              Xuất CSV
            </button>
          </div>

          <div className="overflow-x-auto max-h-[560px]">
            <table className="w-full text-left text-sm">
              <thead className="sticky top-0 bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 border-b border-slate-200">
                <tr>
                  <th className="px-4 py-3">Mã / Thời gian</th>
                  <th className="px-4 py-3">Biển số &amp; Thẻ</th>
                  <th className="px-4 py-3">Loại GD</th>
                  <th className="px-4 py-3">Hình thức</th>
                  <th className="px-4 py-3 text-right">Số tiền</th>
                  <th className="px-4 py-3">Trạng thái</th>
                  <th className="px-4 py-3 text-right">Biên lai</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {transactions.map((t) => (
                  <tr key={t.ma_gd} className="hover:bg-slate-50">
                    <td className="px-4 py-3">
                      <div className="font-semibold text-slate-900">#{t.ma_gd}</div>
                      <div className="text-xs text-slate-500">{formatDateTime(t.giothanhtoan)}</div>
                    </td>
                    <td className="px-4 py-3">
                      <div className="font-mono-plate font-bold text-slate-900">{t.bienso || '—'}</div>
                      <div className="text-xs text-slate-500">
                        {t.mathe ? `Thẻ ${t.mathe}` : ''} {t.tenbaido ? `· ${t.tenbaido}` : ''} {t.vitri ? `(${t.vitri})` : ''}
                      </div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-700">
                      <div>{t.hinhthuc}</div>
                      <div className="text-slate-400">NV: {t.nhanvien}</div>
                    </td>
                    <td className="px-4 py-3 text-xs text-slate-700">{t.loaiphuongtien || '—'}</td>
                    <td className="px-4 py-3 text-right font-bold text-slate-900">
                      {formatVnd(t.chiphi)}
                    </td>
                    <td className="px-4 py-3">
                      {user.role === 'ADMIN' || user.role === 'ACCOUNTANT' ? (
                        <select
                          value={t.trangthai}
                          onChange={(e) => handleStatusChange(t.ma_gd, e.target.value)}
                          className="rounded-lg border border-slate-200 px-2 py-1 text-xs font-semibold"
                        >
                          <option value="Thành công">Thành công</option>
                          <option value="Chờ xử lý">Chờ xử lý</option>
                          <option value="Hoàn tiền">Hoàn tiền</option>
                        </select>
                      ) : (
                        <span className="rounded-full bg-emerald-50 px-2.5 py-0.5 text-xs font-semibold text-emerald-700">
                          {t.trangthai}
                        </span>
                      )}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        onClick={() =>
                          onPrint({
                            kind: 'receipt',
                            id: t.ma_gd,
                            plate: t.bienso || 'N/A',
                            vehicleType: t.loaiphuongtien || undefined,
                            cardCode: t.mathe || undefined,
                            slotLabel: t.tenbaido ? `${t.tenbaido} · ${t.vitri || ''}` : t.vitri || undefined,
                            ticketType: t.hinhthuc,
                            checkinTime: t.giovao || undefined,
                            checkoutTime: t.giothanhtoan,
                            amount: t.chiphi,
                            operatorName: t.nhanvien,
                          })
                        }
                        className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-100"
                      >
                        <Printer className="h-3.5 w-3.5" />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
          <div className="lg:col-span-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
            <div className="flex items-center gap-2.5">
              <div className="rounded-xl bg-indigo-50 p-2.5 text-indigo-600">
                <Clock className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-slate-900">
                  {activeShift ? `Ca đang mở #${activeShift.id}` : 'Mở ca làm việc mới'}
                </h2>
                <p className="text-xs text-slate-500">Nhân viên: {user.full_name}</p>
              </div>
            </div>

            {activeShift ? (
              <form onSubmit={handleCloseShift} className="space-y-4">
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Bắt đầu ca:</span>
                    <span>{formatDateTime(activeShift.started_at)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Tiền đầu ca:</span>
                    <strong>{formatVnd(activeShift.opening_cash)}</strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Thu tiền mặt trong ca:</span>
                    <strong className="text-emerald-600">
                      {formatVnd(activeShift.live_cash_total)}
                    </strong>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Thu chuyển khoản:</span>
                    <strong className="text-indigo-600">
                      {formatVnd(activeShift.live_transfer_total)}
                    </strong>
                  </div>
                  <div className="flex justify-between border-t border-slate-200 pt-2 font-bold">
                    <span>Tiền mặt dự kiến trong két:</span>
                    <span>{formatVnd(activeShift.live_expected_cash)}</span>
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Tiền mặt thực tế kiểm đếm (VNĐ)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={1000}
                    value={actualCash}
                    onChange={(e) => setActualCash(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Ghi chú bàn giao ca
                  </label>
                  <input
                    type="text"
                    value={shiftNote}
                    onChange={(e) => setShiftNote(e.target.value)}
                    placeholder="VD: Đủ tiền, bàn giao cho ca tối"
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full rounded-xl bg-rose-600 py-2.5 text-sm font-bold text-white hover:bg-rose-700"
                >
                  Chốt &amp; Đóng ca làm việc
                </button>
              </form>
            ) : (
              <form onSubmit={handleOpenShift} className="space-y-4">
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Tiền mặt đầu ca (VNĐ)
                  </label>
                  <input
                    type="number"
                    min={0}
                    step={10000}
                    value={openingCash}
                    onChange={(e) => setOpeningCash(Number(e.target.value))}
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2.5 text-sm font-bold"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-slate-600 mb-1">
                    Ghi chú mở ca
                  </label>
                  <input
                    type="text"
                    value={shiftNote}
                    onChange={(e) => setShiftNote(e.target.value)}
                    placeholder="Ca sáng / Ca chiều..."
                    className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm"
                  />
                </div>
                <button
                  type="submit"
                  className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white hover:bg-indigo-700"
                >
                  Bắt đầu ca làm việc
                </button>
              </form>
            )}
          </div>

          <div className="lg:col-span-7 rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <div className="border-b border-slate-200 px-5 py-4 font-bold text-slate-900">
              Lịch sử các ca trực gần đây
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Nhân viên</th>
                    <th className="px-4 py-3">Thời gian</th>
                    <th className="px-4 py-3 text-right">Dự kiến</th>
                    <th className="px-4 py-3 text-right">Thực tế</th>
                    <th className="px-4 py-3">Trạng thái</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shifts.map((s) => (
                    <tr key={s.id}>
                      <td className="px-4 py-3 font-medium text-slate-900">{s.ten_nhanvien}</td>
                      <td className="px-4 py-3 text-xs text-slate-500">
                        <div>Vào: {formatDateTime(s.started_at)}</div>
                        <div>Ra: {formatDateTime(s.ended_at)}</div>
                      </td>
                      <td className="px-4 py-3 text-right font-medium">{formatVnd(s.expected_cash)}</td>
                      <td className="px-4 py-3 text-right font-bold">
                        {s.actual_cash !== null ? formatVnd(s.actual_cash) : '—'}
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            s.status === 'OPEN'
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-slate-100 text-slate-600'
                          }`}
                        >
                          {s.status === 'OPEN' ? 'Đang mở' : 'Đã đóng'}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
