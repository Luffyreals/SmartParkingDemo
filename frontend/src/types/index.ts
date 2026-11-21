export type UserRole = 'ADMIN' | 'ACCOUNTANT' | 'OPERATOR';

export interface AuthUser {
  account_id: number;
  employee_id: number;
  username: string;
  full_name: string;
  role: UserRole;
  lot_id: number | null;
}

export interface OverviewMetrics {
  total_slots: number;
  available_slots: number;
  occupied_slots: number;
  today_revenue: number;
  active_monthly_passes: number;
}

export interface ParkingLot {
  id: number;
  tenbaido: string;
  diadiem: string;
  tong_cho: number;
  cho_trong: number;
  dang_do: number;
  bao_tri: number;
}

export interface ZoneSummary {
  id: number;
  idbdx: number;
  tenbaido: string;
  diadiem: string;
  ten: string;
  tong_cho: number;
  cho_trong: number;
  dang_do: number;
  bao_tri: number;
}

export interface ParkingSlot {
  id: number;
  idkvd: number;
  sothutu: number;
  trangthai: number; // 1: trống, 0: đang đỗ, 2: bảo trì
  ten_khuvuc: string;
  idbdx: number;
  tenbaido: string;
  bienso: string | null;
  giovao: string | null;
  loaiphuongtien: string | null;
}

export interface ActiveTurn {
  id_luotdo: number;
  bienso: string;
  loaiphuongtien: string;
  chu_xe: string;
  tenbaido: string;
  khuvuc: string;
  vitri: number;
  mathe: string;
  giovao: string;
  nhanvien: string;
  loaive: string;
  dongia: number;
}

export interface FeeQuote {
  turn_id: number;
  license_plate: string;
  vehicle_type: string;
  ticket_type: string;
  checkin_time: string;
  checkout_time: string;
  duration_hours: number;
  amount: number;
  is_monthly_pass: boolean;
  monthly_pass_id: number | null;
}

export interface TransactionRecord {
  ma_gd: number;
  bienso: string | null;
  loaiphuongtien: string | null;
  mathe: string | null;
  tenbaido: string | null;
  vitri: string | null;
  giovao: string | null;
  giora: string | null;
  giothanhtoan: string;
  chiphi: number;
  hinhthuc: string;
  loaithanhtoan: string | number;
  ma_ve_thang: number | null;
  trangthai: string;
  nv_tiep_nhan: string | null;
  nhanvien: string;
}

export interface MonthlyPass {
  id: number;
  hoten: string;
  sdt: string;
  cccd: string;
  loaikhachhang: string;
  bienso: string;
  loaiphuongtien: string;
  mathe: string;
  dongia: number;
  ngaybatdau: string;
  ngayketthuc: string;
  trangthai: string; // 'Còn hạn' | 'Hết hạn'
}

export interface Tariff {
  id: number;
  loaive: string;
  dongia: number;
  loaiphuongtien: string;
  loaikhachhang: string;
  idlpt: number;
  idlkh: number;
}

export interface ShiftRecord {
  id: number;
  idnv: number;
  idbdx: number | null;
  ten_nhanvien: string;
  tenbaido: string | null;
  started_at: string;
  ended_at: string | null;
  opening_cash: number;
  expected_cash: number;
  actual_cash: number | null;
  transfer_total: number;
  note: string | null;
  status: 'OPEN' | 'CLOSED';
  live_tx_count?: number;
  live_cash_total?: number;
  live_transfer_total?: number;
  live_expected_cash?: number;
}

export interface OperationalAlerts {
  overdue_turns: Array<{
    id: number;
    bienso: string;
    ma_the: string;
    tenbaido: string;
    khu_vuc: string;
    sothutu: number;
    giovao: string;
    hours_parked: number;
  }>;
  expiring_passes: Array<{
    id: number;
    ten_khachhang: string;
    sdt: string;
    bienso: string;
    ma_the: string;
    ngayketthuc: string;
    days_left: number;
  }>;
  lost_cards: Array<{
    id: number;
    maso: string;
  }>;
}

export interface AuditLog {
  id: number;
  actor_id: number | null;
  actor_username: string;
  action: string;
  entity_type: string;
  entity_id: string | null;
  details_json: string | null;
  created_at: string;
}
