import { CalendarPlus, CreditCard, RefreshCw, Tag, Trash2 } from 'lucide-react';
import { type FormEvent, useEffect, useState } from 'react';
import type { PrintableDocument } from '../components/TicketPrintModal';
import { apiRequest, formatDate, formatVnd } from '../lib/api';
import type { AuthUser, MonthlyPass, Tariff } from '../types';

interface PassesTariffsPageProps {
  user: AuthUser;
  refreshSignal: number;
  onNotify: (type: 'ok' | 'err', msg: string) => void;
  onPrint: (doc: PrintableDocument) => void;
}

export function PassesTariffsPage({
  user,
  refreshSignal,
  onNotify,
  onPrint,
}: PassesTariffsPageProps) {
  const [passes, setPasses] = useState<MonthlyPass[]>([]);
  const [tariffs, setTariffs] = useState<Tariff[]>([]);
  const [vehicleTypes, setVehicleTypes] = useState<Array<{ id: number; tenloai: string }>>([]);
  const [customerTypes, setCustomerTypes] = useState<Array<{ id: number; tenloai: string }>>([]);
  const [cards, setCards] = useState<Array<{ id: number; maso: string }>>([]);

  // Register pass form
  const [hoten, setHoten] = useState('');
  const [sdt, setSdt] = useState('');
  const [cccd, setCccd] = useState('');
  const [custTypeId, setCustTypeId] = useState<number | ''>('');
  const [plate, setPlate] = useState('');
  const [vehTypeId, setVehTypeId] = useState<number | ''>('');
  const [cardId, setCardId] = useState<number | ''>('');
  const [months, setMonths] = useState(1);
  const [payMethod, setPayMethod] = useState<'Tiền mặt' | 'Chuyển khoản'>('Tiền mặt');

  async function loadAll() {
    try {
      const [p, t, cat, availCards] = await Promise.all([
        apiRequest<MonthlyPass[]>('/api/passes'),
        apiRequest<Tariff[]>('/api/tariffs'),
        apiRequest<{
          vehicle_types: Array<{ id: number; tenloai: string }>;
          customer_types: Array<{ id: number; tenloai: string }>;
        }>('/api/catalogs'),
        apiRequest<Array<{ id: number; maso: string }>>('/api/cards?only_available=true'),
      ]);
      setPasses(p);
      setTariffs(t);
      setVehicleTypes(cat.vehicle_types);
      setCustomerTypes(cat.customer_types);
      setCards(availCards);

      if (!vehTypeId && cat.vehicle_types[0]) setVehTypeId(cat.vehicle_types[0].id);
      if (!custTypeId && cat.customer_types[0]) setCustTypeId(cat.customer_types[0].id);
      if (availCards[0] && (!cardId || !availCards.some((c) => c.id === cardId))) {
        setCardId(availCards[0].id);
      }
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  useEffect(() => {
    loadAll();
  }, [refreshSignal]);

  const matchedTariff = tariffs.find(
    (t) =>
      t.loaive.toLowerCase() === 'tháng' &&
      t.idlpt === Number(vehTypeId) &&
      t.idlkh === Number(custTypeId),
  );
  const estimatedCost = (matchedTariff?.dongia || 0) * months;

  async function handleRegister(e: FormEvent) {
    e.preventDefault();
    try {
      const res = await apiRequest<{ id: number }>('/api/passes', {
        method: 'POST',
        body: JSON.stringify({
          hoten,
          sdt,
          cccd,
          customer_type_id: Number(custTypeId),
          license_plate: plate.toUpperCase(),
          vehicle_type_id: Number(vehTypeId),
          card_id: Number(cardId),
          months,
          payment_method: payMethod,
        }),
      });
      onNotify('ok', `Đã đăng ký vé tháng #${res.id} và ghi nhận thanh toán.`);
      onPrint({
        kind: 'receipt',
        id: res.id,
        plate: plate.toUpperCase(),
        ticketType: `Vé tháng (${months} tháng)`,
        checkoutTime: new Date().toISOString(),
        paymentMethod: payMethod,
        amount: estimatedCost,
        operatorName: user.full_name,
      });
      setHoten('');
      setSdt('');
      setCccd('');
      setPlate('');
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleRenew(p: MonthlyPass, addMonths: number) {
    try {
      const res = await apiRequest<{ amount: number; new_end_date: string }>(
        `/api/passes/${p.id}/renew`,
        {
          method: 'POST',
          body: JSON.stringify({ months: addMonths, payment_method: 'Tiền mặt' }),
        },
      );
      onNotify('ok', `Đã gia hạn vé #${p.id} thêm ${addMonths} tháng.`);
      onPrint({
        kind: 'receipt',
        id: p.id,
        plate: p.bienso,
        cardCode: p.mathe,
        ticketType: `Gia hạn vé tháng (+${addMonths} tháng)`,
        checkoutTime: new Date().toISOString(),
        paymentMethod: 'Tiền mặt',
        amount: res.amount,
        operatorName: user.full_name,
      });
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleCancelPass(p: MonthlyPass) {
    if (!window.confirm(`Hủy vé tháng #${p.id} (${p.bienso})?`)) return;
    try {
      await apiRequest(`/api/passes/${p.id}`, { method: 'DELETE' });
      onNotify('ok', `Đã hủy vé tháng #${p.id}.`);
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleUpdateTariffPrice(t: Tariff) {
    const raw = window.prompt(`Nhập đơn giá mới (VNĐ) cho ${t.loaive} · ${t.loaiphuongtien} (${t.loaikhachhang}):`, String(t.dongia));
    if (raw === null) return;
    const price = Number(raw);
    if (Number.isNaN(price) || price < 0) return;
    try {
      await apiRequest(`/api/tariffs/${t.id}`, {
        method: 'PUT',
        body: JSON.stringify({ unit_price: price }),
      });
      onNotify('ok', 'Đã cập nhật bảng giá.');
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  const canManage = user.role === 'ADMIN' || user.role === 'ACCOUNTANT';

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
          Vé tháng &amp; Bảng giá Dịch vụ
        </h1>
        <p className="text-sm text-slate-500">
          Đăng ký, gia hạn vé tháng tự động hạch toán vào giao dịch thu phí và quản lý biểu giá.
        </p>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        {/* Register Form */}
        <div className="xl:col-span-4 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex items-center gap-2.5 mb-5">
            <div className="rounded-xl bg-indigo-50 p-2 text-indigo-600">
              <CalendarPlus className="h-5 w-5" />
            </div>
            <h2 className="font-bold text-slate-900">Đăng ký vé tháng mới</h2>
          </div>

          <form onSubmit={handleRegister} className="space-y-3.5">
            <input
              type="text"
              required
              placeholder="Họ tên khách hàng"
              value={hoten}
              onChange={(e) => setHoten(e.target.value)}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm"
            />
            <div className="grid grid-cols-2 gap-2.5">
              <input
                type="text"
                required
                placeholder="Số điện thoại"
                value={sdt}
                onChange={(e) => setSdt(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm"
              />
              <input
                type="text"
                required
                placeholder="CCCD / CMND"
                value={cccd}
                onChange={(e) => setCccd(e.target.value)}
                className="w-full rounded-xl border border-slate-200 px-3.5 py-2 text-sm"
              />
            </div>
            <div className="grid grid-cols-2 gap-2.5">
              <select
                value={custTypeId}
                onChange={(e) => setCustTypeId(Number(e.target.value))}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                {customerTypes.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.tenloai}
                  </option>
                ))}
              </select>
              <select
                value={vehTypeId}
                onChange={(e) => setVehTypeId(Number(e.target.value))}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                {vehicleTypes.map((v) => (
                  <option key={v.id} value={v.id}>
                    {v.tenloai}
                  </option>
                ))}
              </select>
            </div>
            <input
              type="text"
              required
              placeholder="Biển số xe (VD: 29A-123.45)"
              value={plate}
              onChange={(e) => setPlate(e.target.value.toUpperCase())}
              className="w-full rounded-xl border border-slate-200 px-3.5 py-2 font-mono-plate text-sm font-bold uppercase"
            />
            <div className="grid grid-cols-2 gap-2.5">
              <select
                value={cardId}
                onChange={(e) => setCardId(Number(e.target.value))}
                className="rounded-xl border border-slate-200 px-3 py-2 font-mono-plate text-sm"
              >
                {cards.map((c) => (
                  <option key={c.id} value={c.id}>
                    Thẻ {c.maso}
                  </option>
                ))}
              </select>
              <select
                value={months}
                onChange={(e) => setMonths(Number(e.target.value))}
                className="rounded-xl border border-slate-200 px-3 py-2 text-sm"
              >
                {[1, 2, 3, 6, 12].map((m) => (
                  <option key={m} value={m}>
                    {m} tháng
                  </option>
                ))}
              </select>
            </div>
            <select
              value={payMethod}
              onChange={(e) => setPayMethod(e.target.value as 'Tiền mặt' | 'Chuyển khoản')}
              className="w-full rounded-xl border border-slate-200 px-3 py-2 text-sm"
            >
              <option value="Tiền mặt">Thu tiền mặt</option>
              <option value="Chuyển khoản">Chuyển khoản / VietQR</option>
            </select>

            <div className="rounded-xl bg-indigo-50/70 border border-indigo-100 p-3.5 flex items-center justify-between">
              <span className="text-xs font-semibold text-indigo-900">Thành tiền dự kiến:</span>
              <span className="text-lg font-extrabold text-indigo-700">
                {formatVnd(estimatedCost)}
              </span>
            </div>

            <button
              type="submit"
              disabled={!cardId}
              className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50"
            >
              Đăng ký &amp; Thu tiền
            </button>
          </form>
        </div>

        {/* Passes List & Tariffs */}
        <div className="xl:col-span-8 space-y-6">
          <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <div className="border-b border-slate-200 px-5 py-4 flex items-center justify-between">
              <div className="flex items-center gap-2 font-bold text-slate-900">
                <CreditCard className="h-4 w-4 text-indigo-600" />
                <span>Danh sách vé tháng ({passes.length})</span>
              </div>
            </div>
            <div className="overflow-x-auto max-h-[380px]">
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Khách hàng</th>
                    <th className="px-4 py-3">Biển số &amp; Thẻ</th>
                    <th className="px-4 py-3">Hiệu lực</th>
                    <th className="px-4 py-3">Trạng thái</th>
                    <th className="px-4 py-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {passes.map((p) => {
                    const isValid = p.trangthai === 'Còn hạn';
                    return (
                    <tr key={p.id} className="hover:bg-slate-50">
                      <td className="px-4 py-3">
                        <div className="font-semibold text-slate-900">{p.hoten}</div>
                        <div className="text-xs text-slate-500">
                          {p.loaikhachhang} · {p.sdt}
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-mono-plate font-bold text-slate-900">{p.bienso}</div>
                        <div className="text-xs text-slate-500">
                          {p.loaiphuongtien} · Thẻ {p.mathe}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        <div>Từ: {formatDate(p.ngaybatdau)}</div>
                        <div>Đến: {formatDate(p.ngayketthuc)}</div>
                      </td>
                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2.5 py-0.5 text-xs font-semibold ${
                            isValid
                              ? 'bg-emerald-50 text-emerald-700'
                              : 'bg-rose-50 text-rose-700'
                          }`}
                        >
                          {p.trangthai}
                        </span>
                      </td>
                      <td className="px-4 py-3 text-right">
                        <div className="inline-flex items-center gap-1.5">
                          <button
                            onClick={() => handleRenew(p, 1)}
                            className="inline-flex items-center gap-1 rounded-lg bg-indigo-50 px-2.5 py-1 text-xs font-semibold text-indigo-700 hover:bg-indigo-100"
                          >
                            <RefreshCw className="h-3 w-3" />
                            +1 tháng
                          </button>
                          {canManage && (
                            <button
                              onClick={() => handleCancelPass(p)}
                              className="rounded-lg border border-rose-200 p-1.5 text-rose-600 hover:bg-rose-50"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );})}
                </tbody>
              </table>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
            <div className="border-b border-slate-200 px-5 py-4 flex items-center gap-2 font-bold text-slate-900">
              <Tag className="h-4 w-4 text-amber-600" />
              <span>Bảng giá áp dụng</span>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="bg-slate-50 text-[11px] font-semibold uppercase text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Loại vé</th>
                    <th className="px-4 py-3">Phương tiện</th>
                    <th className="px-4 py-3">Đối tượng</th>
                    <th className="px-4 py-3 text-right">Đơn giá</th>
                    {canManage && <th className="px-4 py-3 text-right">Sửa</th>}
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {tariffs.map((t) => (
                    <tr key={t.id}>
                      <td className="px-4 py-2.5 font-medium capitalize">{t.loaive}</td>
                      <td className="px-4 py-2.5">{t.loaiphuongtien}</td>
                      <td className="px-4 py-2.5 text-slate-600">{t.loaikhachhang}</td>
                      <td className="px-4 py-2.5 text-right font-bold text-slate-900">
                        {formatVnd(t.dongia)}
                      </td>
                      {canManage && (
                        <td className="px-4 py-2.5 text-right">
                          <button
                            onClick={() => handleUpdateTariffPrice(t)}
                            className="rounded-lg border border-slate-200 px-2.5 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                          >
                            Đổi giá
                          </button>
                        </td>
                      )}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
