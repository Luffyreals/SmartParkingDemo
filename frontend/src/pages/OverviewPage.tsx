import {
  Activity,
  Building2,
  Car,
  CheckCircle2,
  CreditCard,
  RefreshCw,
  Wrench,
} from 'lucide-react';
import { useEffect, useMemo, useState } from 'react';
import { apiRequest, formatDateTime, formatVnd } from '../lib/api';
import type { AuthUser, OverviewMetrics, ParkingLot, ParkingSlot, ZoneSummary } from '../types';

interface OverviewPageProps {
  user: AuthUser;
  refreshSignal: number;
  onNotify: (type: 'ok' | 'err', msg: string) => void;
}

export function OverviewPage({ user, refreshSignal, onNotify }: OverviewPageProps) {
  const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
  const [lots, setLots] = useState<ParkingLot[]>([]);
  const [zones, setZones] = useState<ZoneSummary[]>([]);
  const [slots, setSlots] = useState<ParkingSlot[]>([]);
  const [lotFilter, setLotFilter] = useState<number | ''>('');
  const [zoneFilter, setZoneFilter] = useState<number | ''>('');
  const [statusFilter, setStatusFilter] = useState<number | ''>('');
  const [selectedSlot, setSelectedSlot] = useState<ParkingSlot | null>(null);
  const [loading, setLoading] = useState(true);

  async function loadAll() {
    try {
      const [ov, sl] = await Promise.all([
        apiRequest<{ metrics: OverviewMetrics; lots: ParkingLot[]; zones: ZoneSummary[] }>(
          '/api/overview',
        ),
        apiRequest<ParkingSlot[]>('/api/slots'),
      ]);
      setMetrics(ov.metrics);
      setLots(ov.lots);
      setZones(ov.zones);
      setSlots(sl);
    } catch (err: any) {
      onNotify('err', err.message || 'Không tải được dữ liệu tổng quan.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadAll();
  }, [refreshSignal]);

  const filteredZones = useMemo(() => {
    if (!lotFilter) return zones;
    return zones.filter((z) => z.idbdx === Number(lotFilter));
  }, [zones, lotFilter]);

  const filteredSlots = useMemo(() => {
    return slots.filter((s) => {
      if (lotFilter && s.idbdx !== Number(lotFilter)) return false;
      if (zoneFilter && s.idkvd !== Number(zoneFilter)) return false;
      if (statusFilter !== '' && s.trangthai !== Number(statusFilter)) return false;
      return true;
    });
  }, [slots, lotFilter, zoneFilter, statusFilter]);

  async function toggleMaintenance(slot: ParkingSlot) {
    try {
      const toMaint = slot.trangthai !== 2;
      await apiRequest(`/api/slots/${slot.id}/maintenance`, {
        method: 'PATCH',
        body: JSON.stringify({ maintenance: toMaint }),
      });
      onNotify('ok', `Đã ${toMaint ? 'bật bảo trì' : 'mở lại'} ô ${slot.ten_khuvuc}-${slot.sothutu}.`);
      setSelectedSlot(null);
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  async function handleReconcile() {
    try {
      await apiRequest('/api/slots/reconcile', { method: 'POST' });
      onNotify('ok', 'Đã đồng bộ lại toàn bộ trạng thái ô đỗ.');
      await loadAll();
    } catch (err: any) {
      onNotify('err', err.message);
    }
  }

  const kpis = metrics
    ? [
        {
          label: 'Tổng vị trí đỗ',
          value: String(metrics.total_slots),
          sub: `${lots.length} bãi đỗ hoạt động`,
          icon: Building2,
          tone: 'text-slate-700 bg-slate-100',
        },
        {
          label: 'Chỗ còn trống',
          value: String(metrics.available_slots),
          sub: metrics.total_slots
            ? `${Math.round((metrics.available_slots / metrics.total_slots) * 100)}% khả dụng`
            : '0%',
          icon: CheckCircle2,
          tone: 'text-emerald-700 bg-emerald-50',
        },
        {
          label: 'Xe đang gửi',
          value: String(metrics.occupied_slots),
          sub: 'Lượt đỗ đang hoạt động',
          icon: Car,
          tone: 'text-indigo-700 bg-indigo-50',
        },
        {
          label: 'Doanh thu hôm nay',
          value: formatVnd(metrics.today_revenue),
          sub: 'Giao dịch thành công',
          icon: Activity,
          tone: 'text-amber-700 bg-amber-50',
        },
        {
          label: 'Vé tháng hiệu lực',
          value: String(metrics.active_monthly_passes),
          sub: 'Đang còn hạn sử dụng',
          icon: CreditCard,
          tone: 'text-violet-700 bg-violet-50',
        },
      ]
    : [];

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Tổng quan &amp; Sơ đồ Bãi đỗ
          </h1>
          <p className="text-sm text-slate-500">
            Giám sát công suất theo thời gian thực · Nhấp vào từng ô đỗ để xem chi tiết hoặc bảo trì.
          </p>
        </div>
        {user.role === 'ADMIN' && (
          <button
            onClick={handleReconcile}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-50 shadow-xs"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            Đồng bộ trạng thái ô
          </button>
        )}
      </div>

      {/* KPIs */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {loading && !metrics
          ? Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="h-28 rounded-2xl bg-white border border-slate-200 animate-pulse" />
            ))
          : kpis.map((k) => {
              const Icon = k.icon;
              return (
                <div
                  key={k.label}
                  className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs hover:shadow-sm transition"
                >
                  <div className="flex items-center justify-between">
                    <span className="text-xs font-semibold text-slate-500">{k.label}</span>
                    <div className={`rounded-xl p-2 ${k.tone}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                  </div>
                  <div className="mt-3 text-2xl font-extrabold text-slate-900 tracking-tight">
                    {k.value}
                  </div>
                  <div className="mt-1 text-xs text-slate-500">{k.sub}</div>
                </div>
              );
            })}
      </div>

      {/* Lots & Zones Capacity */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {lots.map((lot) => {
          const pct = lot.tong_cho > 0 ? Math.round((lot.dang_do / lot.tong_cho) * 100) : 0;
          return (
            <div key={lot.id} className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
              <div className="flex items-start justify-between gap-2">
                <div>
                  <h3 className="font-bold text-slate-900">{lot.tenbaido}</h3>
                  <p className="text-xs text-slate-500">{lot.diadiem}</p>
                </div>
                <span className="rounded-full bg-indigo-50 px-2.5 py-0.5 text-xs font-bold text-indigo-700">
                  {pct}% đầy
                </span>
              </div>
              <div className="mt-4 h-2 w-full rounded-full bg-slate-100 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${
                    pct >= 85 ? 'bg-rose-500' : pct >= 60 ? 'bg-amber-500' : 'bg-emerald-500'
                  }`}
                  style={{ width: `${pct}%` }}
                />
              </div>
              <div className="mt-3 flex items-center justify-between text-xs text-slate-600">
                <span>Trống: <strong className="text-emerald-600">{lot.cho_trong}</strong></span>
                <span>Đang đỗ: <strong className="text-indigo-600">{lot.dang_do}</strong></span>
                <span>Bảo trì: <strong className="text-amber-600">{lot.bao_tri}</strong></span>
              </div>
            </div>
          );
        })}
      </div>

      {/* Zones Mini Summary */}
      {zones.length > 0 && (
        <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
          {filteredZones.map((z) => (
            <button
              key={z.id}
              onClick={() => setZoneFilter(zoneFilter === z.id ? '' : z.id)}
              className={`rounded-xl border p-3 text-left transition ${
                zoneFilter === z.id
                  ? 'border-indigo-500 bg-indigo-50/70'
                  : 'border-slate-200 bg-white hover:border-slate-300'
              }`}
            >
              <div className="text-xs font-bold text-slate-900">Khu {z.ten}</div>
              <div className="text-[10px] text-slate-500 truncate">{z.tenbaido}</div>
              <div className="mt-1.5 text-xs font-semibold text-emerald-600">
                {z.cho_trong}/{z.tong_cho} trống
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Interactive Slot Grid */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex flex-wrap items-center gap-3">
            <select
              value={lotFilter}
              onChange={(e) => {
                setLotFilter(e.target.value ? Number(e.target.value) : '');
                setZoneFilter('');
              }}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50"
            >
              <option value="">Tất cả bãi đỗ</option>
              {lots.map((l) => (
                <option key={l.id} value={l.id}>
                  {l.tenbaido}
                </option>
              ))}
            </select>

            <select
              value={zoneFilter}
              onChange={(e) => setZoneFilter(e.target.value ? Number(e.target.value) : '')}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50"
            >
              <option value="">Tất cả khu vực</option>
              {filteredZones.map((z) => (
                <option key={z.id} value={z.id}>
                  {z.tenbaido} · Khu {z.ten}
                </option>
              ))}
            </select>

            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value === '' ? '' : Number(e.target.value))}
              className="rounded-xl border border-slate-200 px-3 py-2 text-sm bg-slate-50"
            >
              <option value="">Mọi trạng thái</option>
              <option value="1">Đang trống</option>
              <option value="0">Đang có xe</option>
              <option value="2">Đang bảo trì</option>
            </select>
          </div>

          <div className="flex items-center gap-4 text-xs text-slate-600">
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-sm bg-emerald-100 border border-emerald-400" /> Trống
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-sm bg-indigo-100 border border-indigo-400" /> Đang đỗ
            </span>
            <span className="flex items-center gap-1.5">
              <span className="h-3 w-3 rounded-sm bg-amber-100 border border-amber-400" /> Bảo trì
            </span>
          </div>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8 gap-3">
          {filteredSlots.map((slot) => {
            const isFree = slot.trangthai === 1;
            const isBusy = slot.trangthai === 0;
            return (
              <button
                key={slot.id}
                onClick={() => setSelectedSlot(slot)}
                className={`group rounded-xl border p-3 text-left transition hover:shadow-sm ${
                  isFree
                    ? 'border-emerald-200 bg-emerald-50/50 hover:border-emerald-400'
                    : isBusy
                      ? 'border-indigo-200 bg-indigo-50/60 hover:border-indigo-400'
                      : 'border-amber-200 bg-amber-50/60 hover:border-amber-400'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-bold text-slate-800">
                    {slot.ten_khuvuc}-{slot.sothutu}
                  </span>
                  <span
                    className={`h-2 w-2 rounded-full ${
                      isFree ? 'bg-emerald-500' : isBusy ? 'bg-indigo-500' : 'bg-amber-500'
                    }`}
                  />
                </div>
                <div className="mt-2 truncate font-mono-plate text-xs font-bold text-slate-900">
                  {isBusy ? slot.bienso || 'Có xe' : isFree ? 'Trống' : 'Bảo trì'}
                </div>
                <div className="truncate text-[10px] text-slate-500">{slot.tenbaido}</div>
              </button>
            );
          })}
        </div>
      </div>

      {/* Slot Detail Modal */}
      {selectedSlot && (
        <div className="fixed inset-0 z-40 flex items-center justify-center bg-slate-900/50 p-4 backdrop-blur-xs">
          <div className="w-full max-w-md rounded-2xl bg-white border border-slate-200 p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-lg font-bold text-slate-900">
                Vị trí {selectedSlot.ten_khuvuc}-{selectedSlot.sothutu}
              </h3>
              <span className="text-xs text-slate-500">{selectedSlot.tenbaido}</span>
            </div>

            {selectedSlot.trangthai === 0 ? (
              <div className="rounded-xl bg-indigo-50/70 border border-indigo-200 p-4 space-y-1.5 text-sm">
                <div>
                  Biển số: <strong className="font-mono-plate">{selectedSlot.bienso}</strong>
                </div>
                <div>Loại xe: {selectedSlot.loaiphuongtien}</div>
                <div>Giờ vào: {formatDateTime(selectedSlot.giovao)}</div>
              </div>
            ) : (
              <p className="text-sm text-slate-600">
                Trạng thái hiện tại:{' '}
                <strong>{selectedSlot.trangthai === 1 ? 'Sẵn sàng đón xe' : 'Đang bảo trì'}</strong>
              </p>
            )}

            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setSelectedSlot(null)}
                className="rounded-xl border border-slate-200 px-4 py-2 text-sm"
              >
                Đóng
              </button>
              {selectedSlot.trangthai !== 0 && (
                <button
                  onClick={() => toggleMaintenance(selectedSlot)}
                  className="inline-flex items-center gap-1.5 rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700"
                >
                  <Wrench className="h-4 w-4" />
                  {selectedSlot.trangthai === 2 ? 'Mở lại ô đỗ' : 'Đặt bảo trì'}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
