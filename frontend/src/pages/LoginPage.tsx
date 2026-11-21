import { CarFront, Lock, ShieldCheck, User } from 'lucide-react';
import { type FormEvent, useState } from 'react';
import { apiRequest, setAuthSession } from '../lib/api';
import type { AuthUser } from '../types';

interface LoginPageProps {
  onSuccess: (user: AuthUser) => void;
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('123456');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      const res = await apiRequest<{ access_token: string; user: AuthUser }>('/api/auth/login', {
        method: 'POST',
        body: JSON.stringify({ username, password }),
      });
      setAuthSession(res.access_token, res.user);
      onSuccess(res.user);
    } catch (err: any) {
      setError(err.message || 'Đăng nhập thất bại.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="min-h-screen grid lg:grid-cols-2 bg-slate-50">
      <div className="hidden lg:flex flex-col justify-between bg-slate-900 p-12 text-white relative overflow-hidden">
        <div className="absolute -right-24 -top-24 h-96 w-96 rounded-full bg-indigo-600/20 blur-3xl" />
        <div className="absolute -left-24 -bottom-24 h-96 w-96 rounded-full bg-emerald-500/10 blur-3xl" />

        <div className="relative z-10 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-indigo-600 shadow-lg shadow-indigo-600/30">
            <CarFront className="h-6 w-6 text-white" />
          </div>
          <div>
            <div className="text-lg font-bold tracking-tight">Smart Parking PTIT</div>
            <div className="text-xs text-slate-400">Hệ thống Điều hành Bãi đỗ xe Thông minh</div>
          </div>
        </div>

        <div className="relative z-10 space-y-6 max-w-md">
          <h1 className="text-4xl font-extrabold leading-tight tracking-tight">
            Vận hành làn xe nhanh chóng, đối soát minh bạch từng giao dịch.
          </h1>
          <p className="text-slate-300 text-sm leading-relaxed">
            Kiến trúc FastAPI + WebSocket đồng bộ sơ đồ ô đỗ theo thời gian thực, hỗ trợ phân quyền
            nhân sự, chốt ca thu ngân, nhật ký audit và in phiếu QR trực tiếp qua trình duyệt.
          </p>
          <div className="grid grid-cols-2 gap-4 pt-2">
            <div className="rounded-xl border border-slate-800 bg-slate-800/40 p-4">
              <div className="text-xs text-slate-400">Đồng bộ</div>
              <div className="mt-1 text-base font-bold text-emerald-400">Real-time WebSocket</div>
            </div>
            <div className="rounded-xl border border-slate-800 bg-slate-800/40 p-4">
              <div className="text-xs text-slate-400">Bảo mật</div>
              <div className="mt-1 text-base font-bold text-indigo-400">RBAC &amp; Audit Trail</div>
            </div>
          </div>
        </div>

        <div className="relative z-10 text-xs text-slate-500">
          Nhóm 10 — Học viện Công nghệ Bưu chính Viễn thông (PTIT)
        </div>
      </div>

      <div className="flex items-center justify-center p-6 sm:p-10">
        <div className="w-full max-w-md space-y-6">
          <div className="lg:hidden flex items-center gap-3 mb-4">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-indigo-600">
              <CarFront className="h-5 w-5 text-white" />
            </div>
            <div>
              <div className="font-bold text-slate-900">Smart Parking PTIT</div>
              <div className="text-xs text-slate-500">Hệ thống quản lý bãi đỗ xe</div>
            </div>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-8 shadow-sm">
            <div className="mb-6">
              <h2 className="text-2xl font-bold text-slate-900 tracking-tight">Đăng nhập hệ thống</h2>
              <p className="mt-1 text-sm text-slate-500">
                Sử dụng tài khoản nhân sự được cấp để vận hành hoặc quản trị.
              </p>
            </div>

            {error && (
              <div className="mb-4 rounded-xl border border-rose-200 bg-rose-50 px-4 py-3 text-sm text-rose-700">
                {error}
              </div>
            )}

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Tên đăng nhập
                </label>
                <div className="relative">
                  <User className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="admin"
                    required
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/50 pl-10 pr-4 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-slate-600 mb-1.5">
                  Mật khẩu
                </label>
                <div className="relative">
                  <Lock className="h-4 w-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••"
                    required
                    className="w-full rounded-xl border border-slate-200 bg-slate-50/50 pl-10 pr-4 py-2.5 text-sm text-slate-900 focus:border-indigo-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-indigo-500/20"
                  />
                </div>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full rounded-xl bg-indigo-600 py-2.5 text-sm font-semibold text-white hover:bg-indigo-700 disabled:opacity-60 transition shadow-sm"
              >
                {loading ? 'Đang xác thực...' : 'Đăng nhập'}
              </button>
            </form>

            <div className="mt-6 pt-5 border-t border-slate-100">
              <div className="flex items-center gap-1.5 text-xs font-medium text-slate-500 mb-2.5">
                <ShieldCheck className="h-3.5 w-3.5 text-indigo-600" />
                <span>Chọn nhanh vai trò (mật khẩu mặc định: 123456)</span>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {[
                  { u: 'admin', label: 'Quản lý', role: 'ADMIN' },
                  { u: 'thungan', label: 'Thu ngân', role: 'ACCOUNTANT' },
                  { u: 'baove', label: 'Bảo vệ', role: 'OPERATOR' },
                ].map((acc) => (
                  <button
                    key={acc.u}
                    type="button"
                    onClick={() => {
                      setUsername(acc.u);
                      setPassword('123456');
                    }}
                    className="rounded-lg border border-slate-200 bg-slate-50 px-2.5 py-2 text-left hover:border-indigo-300 hover:bg-indigo-50/50 transition"
                  >
                    <div className="text-xs font-bold text-slate-800">{acc.label}</div>
                    <div className="text-[11px] text-slate-500 font-mono-plate">{acc.u}</div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
