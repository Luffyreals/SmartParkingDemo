import { BarChart3, Building2, Car, TrendingUp } from 'lucide-react';
import { useEffect, useState } from 'react';
import { apiRequest, formatDate, formatVnd } from '../lib/api';

interface AnalyticsSummary {
  daily: Array<{ ngay: string; so_luot: number; doanh_thu: number }>;
  by_vehicle_type: Array<{ loaiphuongtien: string; so_luot: number; doanh_thu: number }>;
  by_lot: Array<{ tenbaido: string; diadiem: string; so_luot: number; doanh_thu: number }>;
  pass_summary: {
    total_passes: number;
    active_passes: number;
    total_pass_revenue: number;
    this_month_pass_revenue: number;
  };
}

export function AnalyticsPage({
  refreshSignal,
  onNotify,
}: {
  refreshSignal: number;
  onNotify: (type: 'ok' | 'err', msg: string) => void;
}) {
  const [days, setDays] = useState(30);
  const [data, setData] = useState<AnalyticsSummary | null>(null);

  useEffect(() => {
    apiRequest<AnalyticsSummary>(`/api/analytics/summary?days=${days}`)
      .then(setData)
      .catch((err: any) => onNotify('err', err.message));
  }, [days, refreshSignal]);

  if (!data) {
    return <div className="p-8 text-sm text-slate-500">Đang tải thống kê doanh thu...</div>;
  }

  const totalRev = data.daily.reduce((s, d) => s + Number(d.doanh_thu || 0), 0);
  const totalTx = data.daily.reduce((s, d) => s + Number(d.so_luot || 0), 0);
  const maxDailyRev = Math.max(1, ...data.daily.map((d) => Number(d.doanh_thu || 0)));
  const maxVehRev = Math.max(1, ...data.by_vehicle_type.map((v) => Number(v.doanh_thu || 0)));

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-extrabold text-slate-900 tracking-tight">
            Thống kê &amp; Phân tích Doanh thu
          </h1>
          <p className="text-sm text-slate-500">
            Tổng hợp doanh thu theo ngày, cơ cấu phương tiện, hiệu suất từng bãi đỗ và vé tháng.
          </p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="rounded-xl border border-slate-200 bg-white px-3.5 py-2 text-sm font-medium"
        >
          <option value={7}>7 ngày gần nhất</option>
          <option value={30}>30 ngày gần nhất</option>
          <option value={90}>90 ngày gần nhất</option>
        </select>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Tổng doanh thu ({days} ngày)</span>
            <TrendingUp className="h-4 w-4 text-emerald-600" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-slate-900">{formatVnd(totalRev)}</div>
          <div className="mt-1 text-xs text-slate-500">{totalTx} giao dịch thành công</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Doanh thu trung bình / ngày</span>
            <BarChart3 className="h-4 w-4 text-indigo-600" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-slate-900">
            {formatVnd(data.daily.length ? Math.round(totalRev / data.daily.length) : 0)}
          </div>
          <div className="mt-1 text-xs text-slate-500">{data.daily.length} ngày có phát sinh</div>
        </div>
        <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-xs">
          <div className="flex items-center justify-between text-xs font-semibold text-slate-500">
            <span>Giá trị danh mục vé tháng</span>
            <Car className="h-4 w-4 text-violet-600" />
          </div>
          <div className="mt-2 text-2xl font-extrabold text-slate-900">
            {formatVnd(data.pass_summary?.total_pass_revenue || 0)}
          </div>
          <div className="mt-1 text-xs text-slate-500">
            {data.pass_summary?.active_passes || 0} / {data.pass_summary?.total_passes || 0} vé đang hiệu lực (tháng này: {formatVnd(data.pass_summary?.this_month_pass_revenue || 0)})
          </div>
        </div>
      </div>

      {/* Daily Bar Chart */}
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs">
        <h2 className="font-bold text-slate-900 mb-4">Biểu đồ doanh thu theo ngày</h2>
        {data.daily.length === 0 ? (
          <p className="text-sm text-slate-500 py-8 text-center">Chưa có dữ liệu trong khoảng thời gian này.</p>
        ) : (
          <div className="flex items-end gap-2 h-52 pt-4 overflow-x-auto">
            {data.daily.map((d) => {
              const h = Math.max(6, Math.round((Number(d.doanh_thu) / maxDailyRev) * 100));
              return (
                <div key={d.ngay} className="group flex-1 min-w-[28px] flex flex-col items-center gap-1.5">
                  <div className="opacity-0 group-hover:opacity-100 transition text-[10px] font-bold text-indigo-700 whitespace-nowrap">
                    {formatVnd(d.doanh_thu)}
                  </div>
                  <div className="w-full flex items-end justify-center h-36">
                    <div
                      className="w-full max-w-[32px] rounded-t-lg bg-indigo-500 group-hover:bg-indigo-600 transition-all"
                      style={{ height: `${h}%` }}
                      title={`${formatDate(d.ngay)}: ${formatVnd(d.doanh_thu)} (${d.so_luot} lượt)`}
                    />
                  </div>
                  <div className="text-[10px] text-slate-500 -rotate-45 origin-top-left whitespace-nowrap">
                    {String(d.ngay).slice(5)}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* By Vehicle Type */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <Car className="h-4 w-4 text-indigo-600" />
            <span>Doanh thu theo loại phương tiện</span>
          </div>
          <div className="space-y-3">
            {data.by_vehicle_type.map((v) => {
              const w = Math.round((Number(v.doanh_thu) / maxVehRev) * 100);
              return (
                <div key={v.loaiphuongtien} className="space-y-1">
                  <div className="flex justify-between text-xs font-medium">
                    <span className="text-slate-700">
                      {v.loaiphuongtien} ({v.so_luot} lượt)
                    </span>
                    <strong className="text-slate-900">{formatVnd(v.doanh_thu)}</strong>
                  </div>
                  <div className="h-2.5 rounded-full bg-slate-100 overflow-hidden">
                    <div className="h-full rounded-full bg-emerald-500" style={{ width: `${w}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* By Lot */}
        <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-xs space-y-4">
          <div className="flex items-center gap-2 font-bold text-slate-900">
            <Building2 className="h-4 w-4 text-amber-600" />
            <span>Doanh thu theo bãi đỗ</span>
          </div>
          <div className="divide-y divide-slate-100">
            {data.by_lot.map((l) => (
              <div key={l.tenbaido} className="py-3 flex items-center justify-between">
                <div>
                  <div className="font-semibold text-sm text-slate-900">{l.tenbaido}</div>
                  <div className="text-xs text-slate-500">
                    {l.diadiem} · {l.so_luot} lượt
                  </div>
                </div>
                <div className="font-bold text-sm text-indigo-700">{formatVnd(l.doanh_thu)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
