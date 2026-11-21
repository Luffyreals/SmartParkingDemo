import {
  ArrowRightLeft,
  Bike,
  Car,
  CreditCard,
  LogIn,
  LogOut,
  Printer,
  QrCode,
  Search,
  Trash2,
} from 'lucide-react';
import { QRCodeSVG } from 'qrcode.react';
import { type FormEvent, useEffect, useMemo, useState } from 'react';
import type { PrintableDocument } from '../components/TicketPrintModal';
import { apiRequest, formatDateTime, formatVnd } from '../lib/api';
import type { ActiveTurn, AuthUser, FeeQuote, ParkingLot, ParkingSlot } from '../types';

interface GatePosPageProps {
  user: AuthUser;
  refreshSignal: number;
  onNotify: (type: 'ok' | 'err', msg: string) => void;
  onPrint: (doc: PrintableDocument) => void;
}

export function GatePosPage({ user, refreshSignal, onNotify, onPrint }: GatePosPageProps) {
  const [lots, setLots] = useState<ParkingLot[]>([]);
  const [vehicleTypes, setVehicleTypes] = useState<Array<{ id: number; tenloai: string }>>([]);
  const [freeSlots, setFreeSlots] = useState<ParkingSlot[]>([]);
  const [cards, setCards] = useState<Array<{ id: number; maso: string }>>([]);
  const [activeTurns, setActiveTurns] = useState<ActiveTurn[]>([]);
  const [loading, setLoading] = useState(true);

  // Check-in state
  const [selectedLotId, setSelectedLotId] = useState<number | ''>('');
  const [plate, setPlate] = useState('');
  const [vehicleTypeId, setVehicleTypeId] = useState<number | ''>('');
  const [slotId, setSlotId] = useState<number | ''>('');
  const [cardId, setCardId] = useState<number | ''>('');
  const [autoPrint, setAutoPrint] = useState(true);
  const [submittingIn, setSubmittingIn] = useState(false);

  // Active turns filter & checkout modal
  const [search, setSearch] = useState('');
  const [checkoutTurn, setCheckoutTurn] = useState<ActiveTurn | null>(null);
  const [quote, setQuote] = useState<FeeQuote | null>(null);
  const [payMethod, setPayMethod] = useState<'Tiền mặt' | 'Chuyển khoản'>('Tiền mặt');
  const [lostCard, setLostCard] = useState(false);
  const [lostFee, setLostFee] = useState(50000);
  const [submittingOut, setSubmittingOut] = useState(false);

  // Move slot modal
  const [moveTurn, setMoveTurn] = useState<ActiveTurn | null>(null);
  const [moveTargetSlotId, setMoveTargetSlotId] = useState<number | ''>('');

  async function loadData() {
    try {
      const [catalogs, turns, slots, availCards] = await Promise.all([
        apiRequest<{ lots: ParkingLot[]; vehicle_types: Array<{ id: number; tenloai: string }> }>(
          '/api/catalogs',
        ),
        apiRequest<ActiveTurn[]>('/api/turns/active'),
        apiRequest<ParkingSlot[]>('/api/slots?status_filter=1'),
        apiRequest<Array<{ id: number; maso: string }>>('/api/cards?only_available=true'),
      ]);
      setLots(catalogs.lots);
      setVehicleTypes(catalogs.vehicle_types);
      setActiveTurns(turns);
      setFreeSlots(slots);
      setCards(availCards);

      if (!vehicleTypeId && catalogs.vehicle_types.length > 0) {
        setVehicleTypeId(catalogs.vehicle_types[0].id);
      }
      if (!selectedLotId && catalogs.lots.length > 0) {
        const defaultLot = user.lot_id || catalogs.lots[0].id;
        setSelectedLotId(defaultLot);
      }
      if (availCards.length > 0 && (!cardId || !availCards.some((c) => c.id === cardId))) {
        setCardId(availCards[0].id);
      }
    } catch (err: any) {
      onNotify('err', err.message || 'Không tải được dữ liệu làn xe.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadData();
  }, [refreshSignal]);

  const slotsForLot = useMemo(() => {
    if (!selectedLotId) return freeSlots;
    return freeSlots.filter((s) => s.idbdx === Number(selectedLotId));
  }, [freeSlots, selectedLotId]);

  useEffect(() => {
    if (slotsForLot.length > 0 && (!slotId || !slotsForLot.some((s) => s.id === slotId))) {
      setSlotId(slotsForLot[0].id);
    } else if (slotsForLot.length === 0) {
      setSlotId('');
    }
  }, [slotsForLot]);

  const filteredTurns = useMemo(() => {
    const q = search.trim().toLowerCase();
    return activeTurns.filter((t) => {
      if (!q) return true;
      return (
        (t.bienso || '').toLowerCase().includes(q) ||
        (t.mathe || '').toLowerCase().includes(q) ||
        (t.khuvuc || '').toLowerCase().includes(q) ||
        (t.tenbaido || '').toLowerCase().includes(q) ||
        (t.chu_xe || '').toLowerCase().includes(q)
      );
    });
  }, [activeTurns, search]);

  async function handleCheckIn(e: FormEvent) {
    e.preventDefault();
    if (!plate.trim() || !vehicleTypeId || !slotId || !cardId) {
      onNotify('err', 'Vui lòng nhập đủ biển số, vị trí đỗ và thẻ RFID.');
      return;
    }
    setSubmittingIn(true);
    try {
      const res = await apiRequest<{ turn_id: number }>('/api/turns/check-in', {
        method: 'POST',
        body: JSON.stringify({
          license_plate: plate.trim().toUpperCase(),
          vehicle_type_id: Number(vehicleTypeId),
          slot_id: Number(slotId),
          card_id: Number(cardId),
          employee_id: user.employee_id,
        }),
      });
      const chosenSlot = freeSlots.find((s) => s.id === Number(slotId));
      const chosenCard = cards.find((c) => c.id === Number(cardId));
      const chosenType = vehicleTypes.find((v) => v.id === Number(vehicleTypeId));

      onNotify('ok', `Xe ${plate.trim().toUpperCase()} đã vào bãi (#${res.turn_id}).`);
      if (autoPrint) {
        onPrint({
          kind: 'ticket',
          id: res.turn_id,
          plate: plate.trim().toUpperCase(),
          vehicleType: chosenType?.tenloai,
          slotLabel: chosenSlot ? `${chosenSlot.tenbaido} · ${chosenSlot.ten_khuvuc}-${chosenSlot.sothutu}` : '',
          cardCode: chosenCard?.maso,
          checkinTime: new Date().toISOString(),
          operatorName: user.full_name,
        });
      }
      setPlate('');
      await loadData();
    } catch (err: any) {
      onNotify('err', err.message || 'Check-in thất bại.');
    } finally {
      setSubmittingIn(false);
    }
  }

  async function openCheckout(turn: ActiveTurn) {
    setCheckoutTurn(turn);
    setLostCard(false);
    setPayMethod('Tiền mặt');
    setQuote(null);
    try {
      const q = await apiRequest<FeeQuote>(`/api/turns/${turn.id_luotdo}/quote`);
      setQuote(q);
    } catch (err: any) {
      onNotify('err', err.message || 'Không tính được phí tạm tính.');
      setCheckoutTurn(null);
    }
  }

  async function handleConfirmCheckout() {
    if (!checkoutTurn || !quote) return;
    setSubmittingOut(true);
    try {
      const res = await apiRequest<{
        turn_id: number;
        amount: number;
        checkout_time: string;
        ticket_type: string;
      }>(`/api/turns/${checkoutTurn.id_luotdo}/check-out`, {
        method: 'POST',
        body: JSON.stringify({
          employee_id: user.employee_id,
          payment_method: payMethod,
          lost_card: lostCard,
          lost_card_fee: lostCard ? Number(lostFee) : 0,
        }),
      });
      onNotify('ok', `Đã cho xe ${checkoutTurn.bienso} ra bãi (${formatVnd(res.amount)}).`);
      onPrint({
        kind: 'receipt',
        id: res.turn_id,
        plate: checkoutTurn.bienso,
        vehicleType: checkoutTurn.loaiphuongtien,
        cardCode: checkoutTurn.mathe,
        slotLabel: `${checkoutTurn.tenbaido} · ${checkoutTurn.khuvuc}-${checkoutTurn.vitri}`,
        ticketType: res.ticket_type,
        checkinTime: checkoutTurn.giovao,
        checkoutTime: res.checkout_time,
        paymentMethod: payMethod,
        amount: res.amount,
        operatorName: user.full_name,
      });
      setCheckoutTurn(null);
      setQuote(null);
      await loadData();
    } catch (err: any) {
      onNotify('err', err.message || 'Thanh toán check-out thất bại.');
    } finally {
      setSubmittingOut(false);
    }
  }

  async function handleMoveSlot() {
    if (!moveTurn || !moveTargetSlotId) return;
    try {
      await apiRequest(`/api/turns/${moveTurn.id_luotdo}/move-slot`, {
        method: 'POST',
        body: JSON.stringify({ new_slot_id: Number(moveTargetSlotId) }),
      });
      onNotify('ok', `Đã chuyển vị trí cho xe ${moveTurn.bienso}.`);
      setMoveTurn(null);
      await loadData();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleCancelTurn(turn: ActiveTurn) {
    if (!window.confirm(`Xác nhận hủy lượt gửi xe ${turn.bienso} (#${turn.id_luotdo})?`)) return;
    try {
      await apiRequest(`/api/turns/${turn.id_luotdo}/cancel`, { method: 'POST' });
      onNotify('ok', `Đã hủy lượt #${turn.id_luotdo} và giải phóng ô đỗ.`);
      await loadData();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  const totalWithLost = quote ? quote.amount + (lostCard ? Number(lostFee || 0) : 0) : 0;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Trạm Làn xe Vào / Ra (Gate POS)
          </h1>
          <p className="text-sm text-slate-500">
            Tối ưu thao tác nhanh tại bốt gác · Tự động chọn vị trí trống và in phiếu QR qua trình duyệt.
          </p>
        </div>
        <div className="flex items-center gap-3 text-xs font-medium text-slate-600 bg-white border border-slate-200 rounded-xl px-3.5 py-2">
          <span>Đang gửi: <strong className="text-indigo-600">{activeTurns.length}</strong> xe</span>
          <span className="text-slate-300">|</span>
          <span>Ô trống: <strong className="text-emerald-600">{freeSlots.length}</strong></span>
          <span className="text-slate-300">|</span>
          <span>Thẻ sẵn sàng: <strong className="text-slate-900">{cards.length}</strong></span>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-12 gap-6 items-start">
        <div className="xl:col-span-5 rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
          <div className="flex items-center justify-between mb-5">
            <div className="flex items-center gap-2.5">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600">
                <LogIn className="h-5 w-5" />
              </div>
              <div>
                <h2 className="font-bold text-slate-900">Ghi nhận xe vào bãi</h2>
                <p className="text-xs text-slate-500">Nhấn Enter để check-in nhanh</p>
              </div>
            </div>
            <label className="flex items-center gap-2 text-xs text-slate-600 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoPrint}
                onChange={(e) => setAutoPrint(e.target.checked)}
                className="rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
              Tự mở in phiếu
            </label>
          </div>

          <form onSubmit={handleCheckIn} className="space-y-4">
            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Biển số xe
              </label>
              <input
                type="text"
                autoFocus
                value={plate}
                onChange={(e) => setPlate(e.target.value.toUpperCase())}
                placeholder="VD: 29A-123.45 hoặc 30K199999"
                maxLength={15}
                className="w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 font-mono-plate text-lg font-bold tracking-wider text-slate-900 uppercase focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Loại phương tiện
              </label>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {vehicleTypes.map((vt) => {
                  const active = Number(vehicleTypeId) === vt.id;
                  const isCar = vt.tenloai.toLowerCase().includes('ô tô');
                  return (
                    <button
                      key={vt.id}
                      type="button"
                      onClick={() => setVehicleTypeId(vt.id)}
                      className={`flex items-center justify-center gap-2 rounded-xl border px-3 py-2.5 text-xs font-semibold transition ${
                        active
                          ? 'border-indigo-600 bg-indigo-50 text-indigo-700 shadow-xs'
                          : 'border-slate-200 bg-white text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {isCar ? <Car className="h-4 w-4" /> : <Bike className="h-4 w-4" />}
                      {vt.tenloai}
                    </button>
                  );
                })}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Bãi đỗ xe
                </label>
                <select
                  value={selectedLotId}
                  onChange={(e) => setSelectedLotId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                >
                  {lots.map((l) => (
                    <option key={l.id} value={l.id}>
                      {l.tenbaido} ({l.cho_trong} trống)
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Vị trí đỗ
                </label>
                <select
                  value={slotId}
                  onChange={(e) => setSlotId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                >
                  {slotsForLot.length === 0 ? (
                    <option value="">Hết chỗ trống</option>
                  ) : (
                    slotsForLot.map((s) => (
                      <option key={s.id} value={s.id}>
                        Khu {s.ten_khuvuc} — Ô {s.sothutu}
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                Thẻ xe RFID cấp phát
              </label>
              <div className="relative">
                <CreditCard className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                <select
                  value={cardId}
                  onChange={(e) => setCardId(e.target.value ? Number(e.target.value) : '')}
                  className="w-full rounded-xl border border-slate-200 bg-white pl-10 pr-3 py-2.5 font-mono-plate text-sm text-slate-800 focus:border-indigo-500 focus:outline-none"
                >
                  {cards.length === 0 ? (
                    <option value="">Không còn thẻ sẵn sàng</option>
                  ) : (
                    cards.map((c) => (
                      <option key={c.id} value={c.id}>
                        Thẻ {c.maso}
                      </option>
                    ))
                  )}
                </select>
              </div>
            </div>

            <button
              type="submit"
              disabled={submittingIn || !slotId || !cardId}
              className="w-full flex items-center justify-center gap-2 rounded-xl bg-indigo-600 py-3 text-sm font-bold text-white hover:bg-indigo-700 disabled:opacity-50 transition shadow-sm"
            >
              <LogIn className="h-4 w-4" />
              {submittingIn ? 'Đang ghi nhận...' : 'Xác nhận Xe vào bãi'}
            </button>
          </form>
        </div>

        <div className="xl:col-span-7 rounded-2xl border border-slate-200 bg-white shadow-xs overflow-hidden">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-200 px-5 py-4">
            <div>
              <h2 className="font-bold text-slate-900">Xe đang gửi trong bãi</h2>
              <p className="text-xs text-slate-500">Chọn xe để tính phí Check-out hoặc chuyển ô</p>
            </div>
            <div className="relative w-full sm:w-64">
              <Search className="h-4 w-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Tìm biển số, mã thẻ, chủ xe..."
                className="w-full rounded-xl border border-slate-200 bg-slate-50 pl-9 pr-3 py-2 text-sm focus:border-indigo-500 focus:bg-white focus:outline-none"
              />
            </div>
          </div>

          <div className="overflow-x-auto max-h-[540px] overflow-y-auto">
            {loading ? (
              <div className="p-10 text-center text-sm text-slate-500">Đang tải danh sách xe...</div>
            ) : filteredTurns.length === 0 ? (
              <div className="p-10 text-center text-sm text-slate-500">
                Không có xe nào khớp điều kiện tìm kiếm.
              </div>
            ) : (
              <table className="w-full text-left text-sm">
                <thead className="sticky top-0 bg-slate-50 text-[11px] font-semibold uppercase tracking-wider text-slate-500 border-b border-slate-200">
                  <tr>
                    <th className="px-4 py-3">Biển số &amp; Chủ xe</th>
                    <th className="px-4 py-3">Thẻ / Vị trí</th>
                    <th className="px-4 py-3">Giờ vào</th>
                    <th className="px-4 py-3 text-right">Thao tác</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {filteredTurns.map((t) => (
                    <tr key={t.id_luotdo} className="hover:bg-slate-50/80 transition">
                      <td className="px-4 py-3">
                        <div className="font-mono-plate font-bold text-slate-900">{t.bienso}</div>
                        <div className="mt-0.5 flex flex-wrap items-center gap-1.5 text-xs text-slate-500">
                          <span>{t.loaiphuongtien}</span>
                          <span>·</span>
                          <span
                            className={`rounded-full px-2 py-0.5 text-[10px] font-semibold ${
                              (t.loaive || '').toLowerCase() === 'tháng'
                                ? 'bg-indigo-50 text-indigo-700'
                                : 'bg-slate-100 text-slate-600'
                            }`}
                          >
                            Vé {t.loaive}
                          </span>
                          <span className="text-slate-400">({t.chu_xe})</span>
                        </div>
                      </td>
                      <td className="px-4 py-3">
                        <div className="font-mono-plate text-xs font-semibold text-slate-800">
                          Thẻ {t.mathe}
                        </div>
                        <div className="text-xs text-slate-500">
                          {t.tenbaido} · {t.khuvuc}-{t.vitri}
                        </div>
                      </td>
                      <td className="px-4 py-3 text-xs text-slate-600">
                        {formatDateTime(t.giovao)}
                      </td>
                      <td className="px-4 py-3">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() =>
                              onPrint({
                                kind: 'ticket',
                                id: t.id_luotdo,
                                plate: t.bienso,
                                vehicleType: t.loaiphuongtien,
                                cardCode: t.mathe,
                                slotLabel: `${t.tenbaido} · ${t.khuvuc}-${t.vitri}`,
                                checkinTime: t.giovao,
                                operatorName: t.nhanvien,
                              })
                            }
                            title="In lại phiếu gửi xe"
                            className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-100"
                          >
                            <Printer className="h-3.5 w-3.5" />
                          </button>
                          <button
                            onClick={() => {
                              setMoveTurn(t);
                              setMoveTargetSlotId(freeSlots[0]?.id || '');
                            }}
                            title="Chuyển ô đỗ"
                            className="rounded-lg border border-slate-200 p-1.5 text-slate-600 hover:bg-slate-100"
                          >
                            <ArrowRightLeft className="h-3.5 w-3.5" />
                          </button>
                          {(user.role === 'ADMIN' || user.role === 'OPERATOR') && (
                            <button
                              onClick={() => handleCancelTurn(t)}
                              title="Hủy lượt gửi"
                              className="rounded-lg border border-rose-200 p-1.5 text-rose-600 hover:bg-rose-50"
                            >
                              <Trash2 className="h-3.5 w-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => openCheckout(t)}
                            className="inline-flex items-center gap-1.5 rounded-lg bg-emerald-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-emerald-700 transition"
                          >
                            <LogOut className="h-3.5 w-3.5" />
                            Ra bãi
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </div>
      </div>

      {checkoutTurn && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-lg rounded-2xl bg-white border border-slate-200 shadow-2xl overflow-hidden">
            <div className="border-b border-slate-200 px-6 py-4 bg-slate-50 flex items-center justify-between">
              <div>
                <h3 className="font-bold text-slate-900">Thanh toán Check-out</h3>
                <p className="text-xs text-slate-500">
                  Lượt #{checkoutTurn.id_luotdo} · Biển số <strong className="font-mono-plate">{checkoutTurn.bienso}</strong>
                </p>
              </div>
              <button
                onClick={() => setCheckoutTurn(null)}
                className="text-xs font-medium text-slate-500 hover:text-slate-800"
              >
                Đóng
              </button>
            </div>

            {!quote ? (
              <div className="p-8 text-center text-sm text-slate-500">Đang tính phí gửi xe...</div>
            ) : (
              <div className="p-6 space-y-4">
                <div className="rounded-xl bg-slate-50 border border-slate-200 p-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-slate-500">Loại vé:</span>
                    <span className="font-semibold text-slate-800">{quote.ticket_type}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Giờ vào:</span>
                    <span>{formatDateTime(quote.checkin_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Giờ ra dự kiến:</span>
                    <span>{formatDateTime(quote.checkout_time)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-slate-500">Thời gian gửi:</span>
                    <span>{quote.duration_hours} giờ</span>
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  {(['Tiền mặt', 'Chuyển khoản'] as const).map((m) => (
                    <button
                      key={m}
                      type="button"
                      onClick={() => setPayMethod(m)}
                      className={`flex items-center justify-center gap-2 rounded-xl border py-2.5 text-sm font-semibold transition ${
                        payMethod === m
                          ? 'border-indigo-600 bg-indigo-50 text-indigo-700'
                          : 'border-slate-200 text-slate-600 hover:bg-slate-50'
                      }`}
                    >
                      {m === 'Chuyển khoản' && <QrCode className="h-4 w-4" />}
                      {m}
                    </button>
                  ))}
                </div>

                {payMethod === 'Chuyển khoản' && totalWithLost > 0 && (
                  <div className="flex items-center gap-4 rounded-xl border border-indigo-200 bg-indigo-50/50 p-3.5">
                    <div className="rounded-lg bg-white p-2 border border-indigo-100">
                      <QRCodeSVG
                        value={`VIETQR|SMARTPARKING|AMOUNT=${totalWithLost}|TURN=${checkoutTurn.id_luotdo}|PLATE=${checkoutTurn.bienso}`}
                        size={84}
                      />
                    </div>
                    <div className="text-xs text-slate-700 space-y-1">
                      <div className="font-bold text-indigo-900">Quét mã thanh toán VietQR</div>
                      <div>Số tiền: <strong>{formatVnd(totalWithLost)}</strong></div>
                      <div>Nội dung: <span className="font-mono-plate">PTIT {checkoutTurn.bienso}</span></div>
                    </div>
                  </div>
                )}

                <div className="rounded-xl border border-amber-200 bg-amber-50/50 p-3.5 space-y-2">
                  <label className="flex items-center gap-2 text-sm font-medium text-amber-900 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={lostCard}
                      onChange={(e) => setLostCard(e.target.checked)}
                      className="rounded border-amber-400 text-amber-600"
                    />
                    Khách báo mất thẻ RFID (khóa thẻ #{checkoutTurn.mathe})
                  </label>
                  {lostCard && (
                    <div className="flex items-center justify-between gap-3 pt-1">
                      <span className="text-xs text-amber-800">Phụ thu mất thẻ (VNĐ):</span>
                      <input
                        type="number"
                        min={0}
                        step={10000}
                        value={lostFee}
                        onChange={(e) => setLostFee(Number(e.target.value))}
                        className="w-36 rounded-lg border border-amber-300 bg-white px-2.5 py-1 text-right text-sm font-semibold"
                      />
                    </div>
                  )}
                </div>

                <div className="flex items-center justify-between border-t border-slate-200 pt-4">
                  <div>
                    <div className="text-xs uppercase font-semibold text-slate-500">Tổng thanh toán</div>
                    <div className="text-2xl font-extrabold text-emerald-600">
                      {formatVnd(totalWithLost)}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      onClick={() => setCheckoutTurn(null)}
                      className="rounded-xl border border-slate-200 px-4 py-2.5 text-sm font-medium text-slate-700 hover:bg-slate-50"
                    >
                      Hủy
                    </button>
                    <button
                      onClick={handleConfirmCheckout}
                      disabled={submittingOut}
                      className="inline-flex items-center gap-2 rounded-xl bg-emerald-600 px-5 py-2.5 text-sm font-bold text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      <Printer className="h-4 w-4" />
                      {submittingOut ? 'Đang xử lý...' : 'Xác nhận & In biên lai'}
                    </button>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {moveTurn && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl space-y-4">
            <h3 className="font-bold text-slate-900">
              Chuyển ô đỗ cho xe <span className="font-mono-plate">{moveTurn.bienso}</span>
            </h3>
            <p className="text-xs text-slate-500">
              Vị trí hiện tại: {moveTurn.tenbaido} · {moveTurn.khuvuc}-{moveTurn.vitri}
            </p>
            <select
              value={moveTargetSlotId}
              onChange={(e) => setMoveTargetSlotId(Number(e.target.value))}
              className="w-full rounded-xl border border-slate-200 px-3 py-2.5 text-sm"
            >
              {freeSlots.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.tenbaido} · Khu {s.ten_khuvuc} — Ô {s.sothutu}
                </option>
              ))}
            </select>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setMoveTurn(null)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm"
              >
                Đóng
              </button>
              <button
                onClick={handleMoveSlot}
                className="rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Xác nhận chuyển
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
