from __future__ import annotations

import html
import json
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Optional

from services.db_service import DBService


class ValidationError(ValueError):
    """Raised when user input violates domain or schema constraints."""


@dataclass(frozen=True)
class OverviewMetrics:
    """Aggregated KPI metrics for the main dashboard."""

    total_slots: int
    available_slots: int
    occupied_slots: int
    active_vehicles: int
    total_revenue: int
    today_revenue: int
    active_monthly_passes: int


@dataclass(frozen=True)
class FeeQuote:
    """Calculated fee summary for a parking turn checkout."""

    turn_id: int
    license_plate: str
    vehicle_type: str
    ticket_type: str
    checkin_time: datetime
    checkout_time: datetime
    duration_hours: float
    amount: int
    is_monthly_pass: bool
    monthly_pass_id: Optional[int]


class ParkingService:
    """Application service handling parking operations, billing, and analytics."""

    def __init__(self, db: DBService) -> None:
        self.db = db

    # ------------------------------------------------------------------
    # Overview & Reference Data
    # ------------------------------------------------------------------

    def get_overview_metrics(self) -> OverviewMetrics:
        """Compute real-time KPI metrics from the database."""
        slot_row = self.db.fetch_one(
            """
            SELECT
                COUNT(*) AS total_slots,
                COALESCE(SUM(CASE WHEN trangthai = 1 THEN 1 ELSE 0 END), 0) AS available_slots,
                COALESCE(SUM(CASE WHEN trangthai = 0 THEN 1 ELSE 0 END), 0) AS occupied_slots
            FROM vitrido
            """
        ) or {}

        active_row = self.db.fetch_one(
            """
            SELECT COUNT(*) AS active_count
            FROM luotdo ld
            WHERE NOT EXISTS (
                SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id
            )
            """
        ) or {}

        rev_row = self.db.fetch_one(
            """
            SELECT
                COALESCE(SUM(chiphi), 0) AS total_revenue,
                COALESCE(SUM(CASE WHEN DATE(giothanhtoan) = CURDATE() THEN chiphi ELSE 0 END), 0) AS today_revenue
            FROM thanhtoan
            WHERE trangthai = 'Thành công'
            """
        ) or {}

        pass_row = self.db.fetch_one(
            """
            SELECT COUNT(*) AS active_passes
            FROM vethang
            WHERE ngaybatdau <= CURDATE() AND ngayketthuc >= CURDATE()
            """
        ) or {}

        return OverviewMetrics(
            total_slots=int(slot_row.get("total_slots") or 0),
            available_slots=int(slot_row.get("available_slots") or 0),
            occupied_slots=int(slot_row.get("occupied_slots") or 0),
            active_vehicles=int(active_row.get("active_count") or 0),
            total_revenue=int(rev_row.get("total_revenue") or 0),
            today_revenue=int(rev_row.get("today_revenue") or 0),
            active_monthly_passes=int(pass_row.get("active_passes") or 0),
        )

    def get_parking_lots(self) -> list[dict[str, Any]]:
        """List all parking lots with slot occupancy summary."""
        return self.db.fetch_all(
            """
            SELECT
                b.id,
                b.tenbaido,
                b.diadiem,
                COUNT(v.id) AS tong_cho,
                COALESCE(SUM(CASE WHEN v.trangthai = 1 THEN 1 ELSE 0 END), 0) AS cho_trong,
                COALESCE(SUM(CASE WHEN v.trangthai = 0 THEN 1 ELSE 0 END), 0) AS dang_do,
                COALESCE(SUM(CASE WHEN v.trangthai = 2 THEN 1 ELSE 0 END), 0) AS bao_tri
            FROM baidoxe b
            LEFT JOIN khuvucdo k ON k.idbdx = b.id
            LEFT JOIN vitrido v ON v.idkvd = k.id
            GROUP BY b.id, b.tenbaido, b.diadiem
            ORDER BY b.id
            """
        )

    def get_zones(self, lot_id: Optional[int] = None) -> list[dict[str, Any]]:
        """Return parking zones, optionally filtered by parking lot."""
        if lot_id is not None:
            return self.db.fetch_all(
                """
                SELECT k.id, k.idbdx, k.ten, b.tenbaido
                FROM khuvucdo k
                JOIN baidoxe b ON b.id = k.idbdx
                WHERE k.idbdx = %s
                ORDER BY k.ten
                """,
                (lot_id,),
            )
        return self.db.fetch_all(
            """
            SELECT k.id, k.idbdx, k.ten, b.tenbaido
            FROM khuvucdo k
            JOIN baidoxe b ON b.id = k.idbdx
            ORDER BY b.id, k.ten
            """
        )

    def get_zones_summary(self, lot_id: Optional[int] = None) -> list[dict[str, Any]]:
        """Return parking zones with slot counts and occupancy."""
        where_clause = "WHERE k.idbdx = %s" if lot_id is not None else ""
        params = (lot_id,) if lot_id is not None else ()
        return self.db.fetch_all(
            f"""
            SELECT
                k.id,
                k.idbdx,
                k.ten,
                b.tenbaido,
                b.diadiem,
                COUNT(v.id) AS tong_cho,
                COALESCE(SUM(CASE WHEN v.trangthai = 1 THEN 1 ELSE 0 END), 0) AS cho_trong,
                COALESCE(SUM(CASE WHEN v.trangthai = 0 THEN 1 ELSE 0 END), 0) AS dang_do,
                COALESCE(SUM(CASE WHEN v.trangthai = 2 THEN 1 ELSE 0 END), 0) AS bao_tri
            FROM khuvucdo k
            JOIN baidoxe b ON b.id = k.idbdx
            LEFT JOIN vitrido v ON v.idkvd = k.id
            {where_clause}
            GROUP BY k.id, k.idbdx, k.ten, b.tenbaido, b.diadiem
            ORDER BY k.idbdx, k.ten
            """,
            params,
        )

    def get_slots(
        self,
        lot_id: Optional[int] = None,
        zone_id: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """Return parking slots with zone, lot, and current parked vehicle info."""
        conditions: list[str] = []
        params: list[Any] = []
        if lot_id is not None:
            conditions.append("b.id = %s")
            params.append(lot_id)
        if zone_id is not None:
            conditions.append("k.id = %s")
            params.append(zone_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        return self.db.fetch_all(
            f"""
            SELECT
                v.id,
                v.idkvd,
                v.sothutu,
                v.trangthai,
                k.ten AS ten_khuvuc,
                b.id AS idbdx,
                b.tenbaido,
                active.bienso,
                active.giovao,
                active.tenloai AS loaiphuongtien
            FROM vitrido v
            JOIN khuvucdo k ON k.id = v.idkvd
            JOIN baidoxe b ON b.id = k.idbdx
            LEFT JOIN (
                SELECT idvtd, bienso, giovao, tenloai
                FROM (
                    SELECT
                        ld.idvtd,
                        pt.bienso,
                        ld.giovao,
                        lpt.tenloai,
                        ROW_NUMBER() OVER (PARTITION BY ld.idvtd ORDER BY ld.id DESC) AS rn
                    FROM luotdo ld
                    JOIN phuongtien pt ON pt.id = ld.idpt
                    JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
                    WHERE NOT EXISTS (
                        SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id
                    )
                ) ranked
                WHERE rn = 1
            ) active ON active.idvtd = v.id
            {where_clause}
            ORDER BY b.id, k.ten, v.sothutu
            """,
            params if params else None,
        )

    def add_slots_to_zone(self, zone_id: int, count: int) -> int:
        """Create additional sequential parking slots in a zone."""
        if count <= 0 or count > 50:
            raise ValidationError("Số lượng ô đỗ thêm mới phải từ 1 đến 50.")

        row = self.db.fetch_one(
            "SELECT COALESCE(MAX(sothutu), 0) AS max_stt FROM vitrido WHERE idkvd = %s",
            (zone_id,),
        )
        start_stt = int((row or {}).get("max_stt") or 0) + 1
        operations = [
            (
                "INSERT INTO vitrido (idkvd, sothutu, trangthai) VALUES (%s, %s, 1)",
                (zone_id, start_stt + i),
            )
            for i in range(count)
        ]
        self.db.execute_transaction(operations)
        return count

    def get_vehicle_types(self) -> list[dict[str, Any]]:
        return self.db.fetch_all("SELECT id, tenloai FROM loaiphuongtien ORDER BY id")

    def get_customer_types(self) -> list[dict[str, Any]]:
        return self.db.fetch_all("SELECT id, tenloai FROM loaikhachhang ORDER BY id")

    def get_tariffs(self) -> list[dict[str, Any]]:
        return self.db.fetch_all(
            """
            SELECT
                bg.id,
                bg.loaive,
                bg.dongia,
                lpt.tenloai AS loaiphuongtien,
                COALESCE(lkh.tenloai, 'Khách vãng lai') AS loaikhachhang,
                bg.idlpt,
                bg.idlkh
            FROM banggia bg
            LEFT JOIN loaiphuongtien lpt ON lpt.id = bg.idlpt
            LEFT JOIN loaikhachhang lkh ON lkh.id = bg.idlkh
            ORDER BY bg.loaive, bg.idlpt, bg.idlkh
            """
        )

    def get_employees(self) -> list[dict[str, Any]]:
        return self.db.fetch_all(
            """
            SELECT nv.id, nv.hoten, nv.chucvu, nv.sdt, nv.idbdx, b.tenbaido
            FROM nhanvien nv
            LEFT JOIN baidoxe b ON b.id = nv.idbdx
            ORDER BY nv.id
            """
        )

    def get_employees_detail(self) -> list[dict[str, Any]]:
        """List staff members with full contact, role, and assigned parking lot."""
        return self.db.fetch_all(
            """
            SELECT
                nv.id,
                nv.hoten,
                nv.chucvu,
                COALESCE(b.tenbaido, 'Toàn hệ thống') AS tenbaido,
                nv.sdt,
                nv.cccd,
                nv.email,
                nv.diachi,
                nv.ngaysinh,
                nv.ngaybatdau
            FROM nhanvien nv
            LEFT JOIN baidoxe b ON b.id = nv.idbdx
            ORDER BY nv.id
            """
        )

    def get_customers_detail(self) -> list[dict[str, Any]]:
        """List registered customers with customer type, plates, and pass counts."""
        return self.db.fetch_all(
            """
            SELECT
                kh.id,
                kh.hoten,
                COALESCE(lkh.tenloai, 'Khác') AS loaikhachhang,
                kh.sdt,
                kh.cccd,
                COALESCE(
                    NULLIF(GROUP_CONCAT(DISTINCT pt.bienso ORDER BY pt.bienso SEPARATOR ', '), ''),
                    '—'
                ) AS bien_so_dang_ky,
                COUNT(DISTINCT CASE WHEN vt.ngayketthuc >= CURDATE() THEN vt.id END) AS so_ve_hieu_luc,
                COUNT(DISTINCT vt.id) AS tong_ve_da_dang_ky
            FROM khachhang kh
            LEFT JOIN loaikhachhang lkh ON lkh.id = kh.idlkh
            LEFT JOIN vethang vt ON vt.idkh = kh.id
            LEFT JOIN phuongtien pt ON pt.id = vt.idpt
            GROUP BY kh.id, kh.hoten, lkh.tenloai, kh.sdt, kh.cccd
            ORDER BY kh.id
            """
        )

    def get_walkin_visitors(self, limit: int = 200) -> list[dict[str, Any]]:
        """List transient / walk-in visitor turns without an active monthly pass."""
        return self.db.fetch_all(
            """
            SELECT
                ld.id AS id_luotdo,
                pt.bienso,
                lpt.tenloai AS loaiphuongtien,
                tx.maso AS mathe,
                CONCAT(b.tenbaido, ' - ', k.ten, ' - Ô ', v.sothutu) AS vitri_do,
                ld.giovao,
                ld.giora,
                nv.hoten AS nhanvien,
                CASE
                    WHEN tt.id IS NULL THEN 'Đang gửi'
                    ELSE 'Đã ra bãi'
                END AS trang_thai,
                COALESCE(tt.chiphi, 0) AS chiphi,
                CASE
                    WHEN tt.id IS NULL THEN 'Chưa thanh toán'
                    WHEN tt.loaithanhtoan = 1 THEN 'Vé tháng'
                    ELSE 'Vé ngày'
                END AS loaithanhtoan
            FROM luotdo ld
            JOIN vitrido v ON v.id = ld.idvtd
            JOIN khuvucdo k ON k.id = v.idkvd
            JOIN baidoxe b ON b.id = k.idbdx
            JOIN nhanvien nv ON nv.id = ld.idnv
            LEFT JOIN phuongtien pt ON pt.id = ld.idpt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            LEFT JOIN thexe tx ON tx.id = ld.idtx
            LEFT JOIN thanhtoan tt ON tt.idld = ld.id
            WHERE tt.idvt IS NULL
              AND NOT EXISTS (
                  SELECT 1
                  FROM vethang vt
                  WHERE vt.idpt = ld.idpt
                    AND vt.ngaybatdau <= DATE(ld.giovao)
                    AND vt.ngayketthuc >= DATE(ld.giovao)
              )
            ORDER BY ld.giovao DESC, ld.id DESC
            LIMIT %s
            """,
            (int(limit),),
        )

    def get_cards(self, only_available: bool = False) -> list[dict[str, Any]]:
        where = "WHERE trangthai = 1" if only_available else ""
        return self.db.fetch_all(
            f"SELECT id, maso, trangthai FROM thexe {where} ORDER BY id"
        )

    def get_cards_detail(self) -> list[dict[str, Any]]:
        """List all RFID parking cards with current turn or monthly pass binding."""
        return self.db.fetch_all(
            """
            SELECT
                tx.id,
                tx.maso,
                tx.trangthai,
                ld_act.bienso AS bienso_dang_gui,
                ld_act.tenbaido,
                ld_act.khuvuc,
                ld_act.sothutu,
                ld_act.giovao,
                vt_act.ma_ve_thang,
                vt_act.chu_ve_thang,
                vt_act.bienso_ve_thang
            FROM thexe tx
            LEFT JOIN (
                SELECT
                    ld.idtx,
                    pt.bienso,
                    b.tenbaido,
                    k.ten AS khuvuc,
                    v.sothutu,
                    ld.giovao,
                    ROW_NUMBER() OVER (PARTITION BY ld.idtx ORDER BY ld.id DESC) AS rn
                FROM luotdo ld
                JOIN vitrido v ON v.id = ld.idvtd
                JOIN khuvucdo k ON k.id = v.idkvd
                JOIN baidoxe b ON b.id = k.idbdx
                LEFT JOIN phuongtien pt ON pt.id = ld.idpt
                WHERE NOT EXISTS (
                    SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id
                )
            ) ld_act ON ld_act.idtx = tx.id AND ld_act.rn = 1
            LEFT JOIN (
                SELECT
                    vt.idtx,
                    vt.id AS ma_ve_thang,
                    kh.hoten AS chu_ve_thang,
                    pt.bienso AS bienso_ve_thang,
                    ROW_NUMBER() OVER (PARTITION BY vt.idtx ORDER BY vt.ngayketthuc DESC, vt.id DESC) AS rn
                FROM vethang vt
                JOIN khachhang kh ON kh.id = vt.idkh
                JOIN phuongtien pt ON pt.id = vt.idpt
                WHERE vt.ngayketthuc >= CURDATE()
            ) vt_act ON vt_act.idtx = tx.id AND vt_act.rn = 1
            ORDER BY tx.id
            """
        )

    def get_vehicles_detail(self) -> list[dict[str, Any]]:
        """List all registered vehicles with turn history and monthly pass status."""
        return self.db.fetch_all(
            """
            SELECT
                pt.id,
                pt.bienso,
                COALESCE(lpt.tenloai, 'Khác') AS loaiphuongtien,
                COUNT(DISTINCT ld.id) AS tong_luot,
                MAX(ld.giovao) AS lan_gui_gan_nhat,
                MAX(
                    CASE
                        WHEN ld.id IS NOT NULL AND NOT EXISTS (
                            SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id
                        ) THEN 1
                        ELSE 0
                    END
                ) AS dang_trong_bai,
                MAX(CASE WHEN vt.ngayketthuc >= CURDATE() THEN 1 ELSE 0 END) AS co_ve_thang,
                COALESCE(MAX(kh.hoten), 'Khách vãng lai') AS chu_xe
            FROM phuongtien pt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            LEFT JOIN luotdo ld ON ld.idpt = pt.id
            LEFT JOIN vethang vt ON vt.idpt = pt.id AND vt.ngayketthuc >= CURDATE()
            LEFT JOIN khachhang kh ON kh.id = vt.idkh
            GROUP BY pt.id, pt.bienso, lpt.tenloai
            ORDER BY lan_gui_gan_nhat DESC, pt.id DESC
            """
        )

    # ------------------------------------------------------------------
    # Check-in / Check-out Operations
    # ------------------------------------------------------------------

    def get_active_turns(self) -> list[dict[str, Any]]:
        """List all vehicles currently parked inside the parking lots."""
        return self.db.fetch_all(
            """
            SELECT
                ld.id AS id_luotdo,
                pt.bienso,
                lpt.tenloai AS loaiphuongtien,
                COALESCE(owner_pass.chu_xe, 'Khách vãng lai') AS chu_xe,
                b.tenbaido,
                k.ten AS khuvuc,
                v.sothutu AS vitri,
                tx.maso AS mathe,
                ld.giovao,
                nv.hoten AS nhanvien,
                bg.loaive,
                bg.dongia
            FROM luotdo ld
            JOIN vitrido v ON v.id = ld.idvtd
            JOIN khuvucdo k ON k.id = v.idkvd
            JOIN baidoxe b ON b.id = k.idbdx
            JOIN nhanvien nv ON nv.id = ld.idnv
            LEFT JOIN phuongtien pt ON pt.id = ld.idpt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            LEFT JOIN thexe tx ON tx.id = ld.idtx
            LEFT JOIN banggia bg ON bg.id = ld.idbg
            LEFT JOIN (
                SELECT idpt, chu_xe
                FROM (
                    SELECT
                        vt.idpt,
                        kh.hoten AS chu_xe,
                        ROW_NUMBER() OVER (PARTITION BY vt.idpt ORDER BY vt.ngayketthuc DESC, vt.id DESC) AS rn
                    FROM vethang vt
                    JOIN khachhang kh ON kh.id = vt.idkh
                    WHERE vt.ngaybatdau <= CURDATE() AND vt.ngayketthuc >= CURDATE()
                ) ranked_pass
                WHERE rn = 1
            ) owner_pass ON owner_pass.idpt = pt.id
            WHERE NOT EXISTS (
                SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id
            )
            ORDER BY ld.giovao DESC
            """
        )

    @staticmethod
    def _normalize_plate(plate: str) -> str:
        normalized = plate.strip().upper().replace(" ", "")
        if not normalized:
            raise ValidationError("Biển số xe không được để trống.")
        if len(normalized) > 8:
            raise ValidationError("Biển số xe tối đa 8 ký tự theo schema DB (ví dụ: 29A12345).")
        return normalized

    def check_in_vehicle(
        self,
        license_plate: str,
        vehicle_type_id: int,
        slot_id: int,
        card_id: int,
        employee_id: int,
    ) -> int:
        """Register a vehicle entering a parking slot atomically."""
        plate = self._normalize_plate(license_plate)
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT id, trangthai FROM vitrido WHERE id = %s FOR UPDATE",
                (slot_id,),
            )
            slot = cursor.fetchone()
            if slot is None or int(slot["trangthai"] or 0) != 1:
                raise ValidationError("Vị trí đỗ đã có xe hoặc không tồn tại.")

            cursor.execute(
                "SELECT id, trangthai FROM thexe WHERE id = %s FOR UPDATE",
                (card_id,),
            )
            card = cursor.fetchone()
            if card is None or int(card["trangthai"] or 0) != 1:
                raise ValidationError("Thẻ xe đang được sử dụng hoặc không hợp lệ.")

            cursor.execute(
                """
                SELECT ld.id
                FROM luotdo ld
                JOIN phuongtien pt ON pt.id = ld.idpt
                WHERE pt.bienso = %s
                  AND NOT EXISTS (SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id)
                LIMIT 1
                """,
                (plate,),
            )
            if cursor.fetchone() is not None:
                raise ValidationError(f"Phương tiện {plate} hiện đang gửi trong bãi.")

            cursor.execute(
                "SELECT id, idlpt FROM phuongtien WHERE bienso = %s",
                (plate,),
            )
            vehicle = cursor.fetchone()
            if vehicle is None:
                cursor.execute(
                    "INSERT INTO phuongtien (bienso, idlpt) VALUES (%s, %s)",
                    (plate, vehicle_type_id),
                )
                vehicle_id = int(cursor.lastrowid)
            else:
                vehicle_id = int(vehicle["id"])

            cursor.execute(
                """
                SELECT id, idbg
                FROM vethang
                WHERE idpt = %s AND ngaybatdau <= CURDATE() AND ngayketthuc >= CURDATE()
                ORDER BY ngayketthuc DESC
                LIMIT 1
                """,
                (vehicle_id,),
            )
            monthly_pass = cursor.fetchone()

            if monthly_pass and monthly_pass.get("idbg"):
                tariff_id = int(monthly_pass["idbg"])
            else:
                cursor.execute(
                    """
                    SELECT id FROM banggia
                    WHERE idlpt = %s AND loaive = 'ngày'
                    ORDER BY id LIMIT 1
                    """,
                    (vehicle_type_id,),
                )
                tariff = cursor.fetchone()
                if tariff is None:
                    raise ValidationError("Không tìm thấy bảng giá ngày phù hợp cho loại xe này.")
                tariff_id = int(tariff["id"])

            cursor.execute(
                "UPDATE vitrido SET trangthai = 0 WHERE id = %s AND trangthai = 1",
                (slot_id,),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Vị trí đỗ đã có xe hoặc không tồn tại.")

            cursor.execute(
                "UPDATE thexe SET trangthai = 0 WHERE id = %s AND trangthai = 1",
                (card_id,),
            )
            if cursor.rowcount != 1:
                raise ValidationError("Thẻ xe đang được sử dụng hoặc không hợp lệ.")

            cursor.execute(
                """
                INSERT INTO luotdo (idvtd, giovao, giora, idnv, idpt, idtx, idbg)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (slot_id, now_str, now_str, employee_id, vehicle_id, card_id, tariff_id),
            )
            return int(cursor.lastrowid)

    def get_fee_quote(self, turn_id: int) -> FeeQuote:
        """Calculate checkout fee for an active parking turn."""
        row = self.db.fetch_one(
            """
            SELECT
                ld.id,
                ld.giovao,
                ld.idpt,
                pt.bienso,
                lpt.tenloai AS loaiphuongtien,
                bg.loaive,
                bg.dongia
            FROM luotdo ld
            JOIN phuongtien pt ON pt.id = ld.idpt
            JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            LEFT JOIN banggia bg ON bg.id = ld.idbg
            WHERE ld.id = %s
              AND NOT EXISTS (SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id)
            """,
            (turn_id,),
        )
        if row is None:
            raise ValidationError("Không tìm thấy lượt đỗ đang hoạt động.")

        checkin_dt = row["giovao"]
        if isinstance(checkin_dt, str):
            checkin_dt = datetime.fromisoformat(checkin_dt)
        checkout_dt = datetime.now()
        hours = max((checkout_dt - checkin_dt).total_seconds() / 3600.0, 0.0)

        monthly_pass = self.db.fetch_one(
            """
            SELECT id
            FROM vethang
            WHERE idpt = %s AND ngaybatdau <= CURDATE() AND ngayketthuc >= CURDATE()
            ORDER BY ngayketthuc DESC
            LIMIT 1
            """,
            (row["idpt"],),
        )

        is_monthly = monthly_pass is not None or str(row.get("loaive") or "") == "tháng"
        if is_monthly:
            amount = 0
        else:
            unit_price = int(row.get("dongia") or 5000)
            days = max(1, int(hours // 24) + (1 if hours % 24 > 0 or hours == 0 else 0))
            amount = unit_price * days

        return FeeQuote(
            turn_id=int(row["id"]),
            license_plate=str(row["bienso"]),
            vehicle_type=str(row["loaiphuongtien"]),
            ticket_type="Vé tháng" if is_monthly else "Vé ngày",
            checkin_time=checkin_dt,
            checkout_time=checkout_dt,
            duration_hours=round(hours, 2),
            amount=amount,
            is_monthly_pass=is_monthly,
            monthly_pass_id=int(monthly_pass["id"]) if monthly_pass else None,
        )

    def check_out_vehicle(
        self,
        turn_id: int,
        employee_id: int,
        lost_card: bool = False,
        lost_card_fee: int = 0,
    ) -> FeeQuote:
        """Complete parking turn, record payment, and free slot & card atomically."""
        if lost_card and lost_card_fee < 0:
            raise ValidationError("Phụ phí mất thẻ không được âm.")

        quote = self.get_fee_quote(turn_id)
        final_amount = quote.amount + (lost_card_fee if lost_card else 0)
        final_quote = FeeQuote(
            turn_id=quote.turn_id,
            license_plate=quote.license_plate,
            vehicle_type=quote.vehicle_type,
            ticket_type=f"{quote.ticket_type} (Mất thẻ)" if lost_card else quote.ticket_type,
            checkin_time=quote.checkin_time,
            checkout_time=quote.checkout_time,
            duration_hours=quote.duration_hours,
            amount=final_amount,
            is_monthly_pass=quote.is_monthly_pass,
            monthly_pass_id=quote.monthly_pass_id,
        )
        now_str = final_quote.checkout_time.strftime("%Y-%m-%d %H:%M:%S")
        next_card_status = 2 if lost_card else 1

        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT id, idvtd, idtx FROM luotdo WHERE id = %s FOR UPDATE",
                (turn_id,),
            )
            turn = cursor.fetchone()
            if turn is None:
                raise ValidationError("Lượt đỗ không tồn tại.")

            cursor.execute(
                "SELECT id FROM thanhtoan WHERE idld = %s LIMIT 1",
                (turn_id,),
            )
            if cursor.fetchone() is not None:
                raise ValidationError("Lượt đỗ này đã được thanh toán trước đó.")

            cursor.execute(
                "UPDATE luotdo SET giora = %s WHERE id = %s",
                (now_str, turn_id),
            )
            cursor.execute(
                """
                INSERT INTO thanhtoan (idld, chiphi, giothanhtoan, trangthai, idnv, loaithanhtoan, idvt)
                VALUES (%s, %s, %s, 'Thành công', %s, %s, %s)
                """,
                (
                    turn_id,
                    final_quote.amount,
                    now_str,
                    employee_id,
                    1 if final_quote.is_monthly_pass else 0,
                    final_quote.monthly_pass_id,
                ),
            )
            cursor.execute(
                "UPDATE vitrido SET trangthai = 1 WHERE id = %s",
                (turn["idvtd"],),
            )
            cursor.execute(
                "UPDATE thexe SET trangthai = %s WHERE id = %s",
                (next_card_status, turn["idtx"]),
            )

        return final_quote

    # ------------------------------------------------------------------
    # Transactions & Analytics
    # ------------------------------------------------------------------

    def get_transactions(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        vehicle_type_id: Optional[int] = None,
        limit: int = 200,
    ) -> list[dict[str, Any]]:
        """Query payment history with optional date and vehicle type filters."""
        conditions: list[str] = []
        params: list[Any] = []
        if date_from is not None:
            conditions.append("DATE(tt.giothanhtoan) >= %s")
            params.append(date_from.strftime("%Y-%m-%d"))
        if date_to is not None:
            conditions.append("DATE(tt.giothanhtoan) <= %s")
            params.append(date_to.strftime("%Y-%m-%d"))
        if vehicle_type_id is not None:
            conditions.append("pt.idlpt = %s")
            params.append(vehicle_type_id)

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)

        return self.db.fetch_all(
            f"""
            SELECT
                tt.id AS ma_gd,
                COALESCE(pt.bienso, pt_vt.bienso) AS bienso,
                COALESCE(lpt.tenloai, lpt_vt.tenloai) AS loaiphuongtien,
                COALESCE(tx.maso, tx_vt.maso) AS mathe,
                b.tenbaido,
                CASE
                    WHEN k.ten IS NOT NULL AND v.sothutu IS NOT NULL THEN CONCAT(k.ten, '-', v.sothutu)
                    ELSE 'Vé tháng'
                END AS vitri,
                ld.giovao,
                ld.giora,
                tt.giothanhtoan,
                tt.chiphi,
                CASE
                    WHEN tt.idvt IS NOT NULL AND tt.idld IS NULL THEN 'Đăng ký/Gia hạn vé tháng'
                    WHEN tt.loaithanhtoan IN ('1', 'Vé tháng') THEN 'Vé tháng'
                    WHEN tt.loaithanhtoan IN ('0', 'Vé ngày') THEN 'Vé ngày'
                    ELSE tt.loaithanhtoan
                END AS hinhthuc,
                tt.loaithanhtoan,
                tt.idvt AS ma_ve_thang,
                tt.trangthai,
                nv_in.hoten AS nv_tiep_nhan,
                nv.hoten AS nhanvien
            FROM thanhtoan tt
            LEFT JOIN luotdo ld ON ld.id = tt.idld
            LEFT JOIN vitrido v ON v.id = ld.idvtd
            LEFT JOIN khuvucdo k ON k.id = v.idkvd
            LEFT JOIN baidoxe b ON b.id = k.idbdx
            JOIN nhanvien nv ON nv.id = tt.idnv
            LEFT JOIN nhanvien nv_in ON nv_in.id = ld.idnv
            LEFT JOIN thexe tx ON tx.id = ld.idtx
            LEFT JOIN phuongtien pt ON pt.id = ld.idpt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            LEFT JOIN vethang vt ON vt.id = tt.idvt
            LEFT JOIN thexe tx_vt ON tx_vt.id = vt.idtx
            LEFT JOIN phuongtien pt_vt ON pt_vt.id = vt.idpt
            LEFT JOIN loaiphuongtien lpt_vt ON lpt_vt.id = pt_vt.idlpt
            {where_clause}
            ORDER BY tt.giothanhtoan DESC
            LIMIT %s
            """,
            params,
        )

    def get_daily_revenue(self, days: int = 30) -> list[dict[str, Any]]:
        """Aggregate daily revenue and parking turn counts."""
        return self.db.fetch_all(
            """
            SELECT
                DATE(giothanhtoan) AS ngay,
                COUNT(*) AS so_luot,
                COALESCE(SUM(chiphi), 0) AS doanh_thu
            FROM thanhtoan
            WHERE trangthai = 'Thành công'
              AND giothanhtoan >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY DATE(giothanhtoan)
            ORDER BY ngay ASC
            """,
            (days,),
        )

    def get_revenue_by_vehicle_type(self) -> list[dict[str, Any]]:
        """Aggregate revenue and turns grouped by vehicle type."""
        return self.db.fetch_all(
            """
            SELECT
                COALESCE(lpt.tenloai, 'Khác') AS loaiphuongtien,
                COUNT(tt.id) AS so_luot,
                COALESCE(SUM(tt.chiphi), 0) AS doanh_thu
            FROM thanhtoan tt
            JOIN luotdo ld ON ld.id = tt.idld
            LEFT JOIN phuongtien pt ON pt.id = ld.idpt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            WHERE tt.trangthai = 'Thành công'
            GROUP BY lpt.tenloai
            ORDER BY doanh_thu DESC
            """
        )

    def get_revenue_by_lot(self) -> list[dict[str, Any]]:
        """Aggregate revenue and turns grouped by parking lot."""
        return self.db.fetch_all(
            """
            SELECT
                b.tenbaido,
                b.diadiem,
                COUNT(tt.id) AS so_luot,
                COALESCE(SUM(tt.chiphi), 0) AS doanh_thu
            FROM thanhtoan tt
            JOIN luotdo ld ON ld.id = tt.idld
            JOIN vitrido v ON v.id = ld.idvtd
            JOIN khuvucdo k ON k.id = v.idkvd
            JOIN baidoxe b ON b.id = k.idbdx
            WHERE tt.trangthai = 'Thành công'
            GROUP BY b.id, b.tenbaido, b.diadiem
            ORDER BY doanh_thu DESC
            """
        )

    # ------------------------------------------------------------------
    # Monthly Passes & Customers
    # ------------------------------------------------------------------

    def get_monthly_passes(self) -> list[dict[str, Any]]:
        return self.db.fetch_all(
            """
            SELECT
                vt.id,
                kh.hoten,
                kh.sdt,
                kh.cccd,
                lkh.tenloai AS loaikhachhang,
                pt.bienso,
                lpt.tenloai AS loaiphuongtien,
                tx.maso AS mathe,
                bg.dongia,
                vt.ngaybatdau,
                vt.ngayketthuc,
                CASE
                    WHEN vt.ngayketthuc >= CURDATE() THEN 'Còn hạn'
                    ELSE 'Hết hạn'
                END AS trangthai
            FROM vethang vt
            JOIN khachhang kh ON kh.id = vt.idkh
            LEFT JOIN loaikhachhang lkh ON lkh.id = kh.idlkh
            LEFT JOIN phuongtien pt ON pt.id = vt.idpt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
            LEFT JOIN thexe tx ON tx.id = vt.idtx
            LEFT JOIN banggia bg ON bg.id = vt.idbg
            ORDER BY vt.id DESC
            """
        )

    def register_monthly_pass(
        self,
        hoten: str,
        sdt: str,
        cccd: str,
        customer_type_id: int,
        license_plate: str,
        vehicle_type_id: int,
        card_id: int,
        months: int = 1,
        employee_id: Optional[int] = None,
        payment_method: str = "Tiền mặt",
    ) -> int:
        """Register or renew a monthly parking pass for a customer and vehicle."""
        hoten_clean = hoten.strip()
        sdt_clean = sdt.strip()
        cccd_clean = cccd.strip()
        if not hoten_clean or len(hoten_clean) > 30:
            raise ValidationError("Họ tên khách hàng phải từ 1 đến 30 ký tự.")
        if not sdt_clean or len(sdt_clean) > 20:
            raise ValidationError("Số điện thoại không hợp lệ (tối đa 20 ký tự).")
        if not cccd_clean or len(cccd_clean) > 15:
            raise ValidationError("CCCD không hợp lệ (tối đa 15 ký tự).")
        if months < 1 or months > 12:
            raise ValidationError("Số tháng đăng ký phải từ 1 đến 12.")

        plate = self._normalize_plate(license_plate)
        start_date = date.today()
        end_date = start_date + timedelta(days=30 * months)

        with self.db.transaction() as cursor:
            cursor.execute(
                """
                SELECT id, dongia FROM banggia
                WHERE loaive = 'tháng' AND idlpt = %s AND idlkh = %s
                LIMIT 1
                """,
                (vehicle_type_id, customer_type_id),
            )
            tariff = cursor.fetchone()
            if tariff is None:
                raise ValidationError("Không tìm thấy đơn giá vé tháng cho cấu hình này.")

            cursor.execute(
                "SELECT id, trangthai FROM thexe WHERE id = %s FOR UPDATE",
                (card_id,),
            )
            card = cursor.fetchone()
            if card is None or int(card["trangthai"]) != 1:
                raise ValidationError("Thẻ xe không ở trạng thái sẵn sàng.")

            cursor.execute(
                """
                SELECT id FROM vethang
                WHERE idtx = %s AND ngayketthuc >= CURDATE()
                LIMIT 1
                """,
                (card_id,),
            )
            if cursor.fetchone() is not None:
                raise ValidationError("Thẻ xe đang được gắn với một vé tháng khác còn hiệu lực.")

            cursor.execute("SELECT id FROM khachhang WHERE cccd = %s FOR UPDATE", (cccd_clean,))
            customer = cursor.fetchone()
            if customer is None:
                cursor.execute(
                    "INSERT INTO khachhang (hoten, sdt, cccd, idlkh) VALUES (%s, %s, %s, %s)",
                    (hoten_clean, sdt_clean, cccd_clean, customer_type_id),
                )
                customer_id = int(cursor.lastrowid)
            else:
                customer_id = int(customer["id"])

            cursor.execute("SELECT id FROM phuongtien WHERE bienso = %s FOR UPDATE", (plate,))
            vehicle = cursor.fetchone()
            if vehicle is None:
                cursor.execute(
                    "INSERT INTO phuongtien (bienso, idlpt) VALUES (%s, %s)",
                    (plate, vehicle_type_id),
                )
                vehicle_id = int(cursor.lastrowid)
            else:
                vehicle_id = int(vehicle["id"])

            cursor.execute(
                """
                INSERT INTO vethang (ngaybatdau, ngayketthuc, idtx, idpt, idbg, idkh)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (start_date, end_date, card_id, vehicle_id, int(tariff["id"]), customer_id),
            )
            pass_id = int(cursor.lastrowid)
            if employee_id is not None:
                amount = int(tariff.get("dongia") or 0) * months
                cursor.execute(
                    """
                    INSERT INTO thanhtoan (idld, chiphi, giothanhtoan, trangthai, idnv, loaithanhtoan, idvt)
                    VALUES (NULL, %s, NOW(), 'Thành công', %s, %s, %s)
                    """,
                    (amount, employee_id, payment_method, pass_id),
                )
            return pass_id

    # ------------------------------------------------------------------
    # Validation & ID Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_text(value: str, label: str, max_len: int) -> str:
        """Validate non-empty text within schema column length."""
        cleaned = value.strip()
        if not cleaned:
            raise ValidationError(f"{label} không được để trống.")
        if len(cleaned) > max_len:
            raise ValidationError(f"{label} tối đa {max_len} ký tự.")
        return cleaned

    @staticmethod
    def _next_manual_id(cursor: Any, table: str) -> int:
        """Compute next primary key inside a transaction for tables without AUTO_INCREMENT."""
        cursor.execute(f"SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM {table} FOR UPDATE")
        row = cursor.fetchone()
        return int((row or {}).get("next_id") or 1)

    # ------------------------------------------------------------------
    # CRUD: Parking Lots, Zones & Slots
    # ------------------------------------------------------------------

    def create_parking_lot(self, name: str, location: str) -> int:
        """Create a new parking lot."""
        lot_name = self._require_text(name, "Tên bãi đỗ", 20)
        lot_loc = self._require_text(location, "Địa điểm", 30)
        return self.db.execute_non_query(
            "INSERT INTO baidoxe (tenbaido, diadiem) VALUES (%s, %s)",
            (lot_name, lot_loc),
        )

    def update_parking_lot(self, lot_id: int, name: str, location: str) -> None:
        """Update an existing parking lot."""
        lot_name = self._require_text(name, "Tên bãi đỗ", 20)
        lot_loc = self._require_text(location, "Địa điểm", 30)
        self.db.execute_non_query(
            "UPDATE baidoxe SET tenbaido = %s, diadiem = %s WHERE id = %s",
            (lot_name, lot_loc, lot_id),
        )

    def delete_parking_lot(self, lot_id: int) -> None:
        """Delete a parking lot if it has no zones or employees."""
        zone_ref = self.db.fetch_one("SELECT id FROM khuvucdo WHERE idbdx = %s LIMIT 1", (lot_id,))
        if zone_ref is not None:
            raise ValidationError("Không thể xóa bãi đỗ đang có khu vực đỗ.")
        emp_ref = self.db.fetch_one("SELECT id FROM nhanvien WHERE idbdx = %s LIMIT 1", (lot_id,))
        if emp_ref is not None:
            raise ValidationError("Không thể xóa bãi đỗ đang có nhân viên phụ trách.")
        self.db.execute_non_query("DELETE FROM baidoxe WHERE id = %s", (lot_id,))

    def create_zone(self, lot_id: int, name: str) -> int:
        """Create a new parking zone inside a lot."""
        zone_name = self._require_text(name, "Tên khu vực", 5)
        dup = self.db.fetch_one(
            "SELECT id FROM khuvucdo WHERE idbdx = %s AND UPPER(ten) = UPPER(%s) LIMIT 1",
            (lot_id, zone_name),
        )
        if dup is not None:
            raise ValidationError(f"Khu vực '{zone_name}' đã tồn tại trong bãi đỗ này.")
        return self.db.execute_non_query(
            "INSERT INTO khuvucdo (idbdx, ten) VALUES (%s, %s)",
            (lot_id, zone_name),
        )

    def update_zone(self, zone_id: int, lot_id: int, name: str) -> None:
        """Update zone name or parent lot."""
        zone_name = self._require_text(name, "Tên khu vực", 5)
        dup = self.db.fetch_one(
            "SELECT id FROM khuvucdo WHERE idbdx = %s AND UPPER(ten) = UPPER(%s) AND id <> %s LIMIT 1",
            (lot_id, zone_name, zone_id),
        )
        if dup is not None:
            raise ValidationError(f"Khu vực '{zone_name}' đã tồn tại trong bãi đỗ này.")
        self.db.execute_non_query(
            "UPDATE khuvucdo SET idbdx = %s, ten = %s WHERE id = %s",
            (lot_id, zone_name, zone_id),
        )

    def delete_zone(self, zone_id: int) -> None:
        """Delete a zone if it contains no parking slots."""
        slot_ref = self.db.fetch_one("SELECT id FROM vitrido WHERE idkvd = %s LIMIT 1", (zone_id,))
        if slot_ref is not None:
            raise ValidationError("Không thể xóa khu vực đang có vị trí đỗ.")
        self.db.execute_non_query("DELETE FROM khuvucdo WHERE id = %s", (zone_id,))

    def set_slot_maintenance(self, slot_id: int, maintenance: bool) -> None:
        """Toggle a free parking slot between available (1) and maintenance (2)."""
        with self.db.transaction() as cursor:
            cursor.execute("SELECT id, trangthai FROM vitrido WHERE id = %s FOR UPDATE", (slot_id,))
            slot = cursor.fetchone()
            if slot is None:
                raise ValidationError("Vị trí đỗ không tồn tại.")
            status = int(slot["trangthai"])
            if maintenance:
                if status == 0:
                    raise ValidationError("Vị trí đang có xe đỗ, không thể khóa bảo trì.")
                if status == 2:
                    raise ValidationError("Vị trí đã ở trạng thái bảo trì.")
                cursor.execute("UPDATE vitrido SET trangthai = 2 WHERE id = %s", (slot_id,))
            else:
                if status != 2:
                    raise ValidationError("Vị trí không ở trạng thái bảo trì.")
                cursor.execute("UPDATE vitrido SET trangthai = 1 WHERE id = %s", (slot_id,))

    def delete_slot(self, slot_id: int) -> None:
        """Delete an unused parking slot that has no turn history."""
        with self.db.transaction() as cursor:
            cursor.execute("SELECT id, trangthai FROM vitrido WHERE id = %s FOR UPDATE", (slot_id,))
            slot = cursor.fetchone()
            if slot is None:
                raise ValidationError("Vị trí đỗ không tồn tại.")
            if int(slot["trangthai"]) == 0:
                raise ValidationError("Vị trí đang có xe đỗ, không thể xóa.")
            cursor.execute("SELECT id FROM luotdo WHERE idvtd = %s LIMIT 1", (slot_id,))
            if cursor.fetchone() is not None:
                raise ValidationError("Vị trí đã có lịch sử lượt đỗ, chỉ có thể khóa bảo trì.")
            cursor.execute("DELETE FROM vitrido WHERE id = %s", (slot_id,))

    # ------------------------------------------------------------------
    # CRUD: Tariffs
    # ------------------------------------------------------------------

    def create_tariff(
        self,
        ticket_type: str,
        unit_price: int,
        vehicle_type_id: int,
        customer_type_id: Optional[int],
    ) -> int:
        """Create a new tariff entry in banggia."""
        t_type = ticket_type.strip().lower()
        if t_type not in ("ngày", "tháng"):
            raise ValidationError("Loại vé chỉ nhận 'ngày' hoặc 'tháng'.")
        if unit_price < 0:
            raise ValidationError("Đơn giá không được âm.")
        return self.db.execute_non_query(
            """
            INSERT INTO banggia (loaive, dongia, idlpt, idlkh)
            VALUES (%s, %s, %s, %s)
            """,
            (t_type, unit_price, vehicle_type_id, customer_type_id),
        )

    def update_tariff(self, tariff_id: int, unit_price: int) -> None:
        """Update unit price for an existing tariff."""
        if unit_price < 0:
            raise ValidationError("Đơn giá không được âm.")
        self.db.execute_non_query(
            "UPDATE banggia SET dongia = %s WHERE id = %s",
            (unit_price, tariff_id),
        )

    def delete_tariff(self, tariff_id: int) -> None:
        """Delete a tariff if not referenced by turns or monthly passes."""
        if self.db.fetch_one("SELECT id FROM luotdo WHERE idbg = %s LIMIT 1", (tariff_id,)) is not None:
            raise ValidationError("Bảng giá đã phát sinh lượt đỗ, không thể xóa.")
        if self.db.fetch_one("SELECT id FROM vethang WHERE idbg = %s LIMIT 1", (tariff_id,)) is not None:
            raise ValidationError("Bảng giá đã gắn với vé tháng, không thể xóa.")
        self.db.execute_non_query("DELETE FROM banggia WHERE id = %s", (tariff_id,))

    # ------------------------------------------------------------------
    # CRUD: Employees
    # ------------------------------------------------------------------

    def create_employee(
        self,
        lot_id: Optional[int],
        full_name: str,
        address: str,
        birth_date: date,
        role: str,
        phone: str,
        start_date: date,
        email: str,
        cccd: str,
    ) -> int:
        """Create a new employee with transaction-safe ID allocation."""
        clean_name = self._require_text(full_name, "Họ tên", 30)
        clean_addr = self._require_text(address, "Địa chỉ", 50)
        clean_role = self._require_text(role, "Chức vụ", 10)
        clean_phone = self._require_text(phone, "Số điện thoại", 10)
        clean_email = self._require_text(email, "Email", 30)
        clean_cccd = self._require_text(cccd, "CCCD", 15)

        with self.db.transaction() as cursor:
            cursor.execute("SELECT id FROM nhanvien WHERE cccd = %s LIMIT 1", (clean_cccd,))
            if cursor.fetchone() is not None:
                raise ValidationError(f"CCCD {clean_cccd} đã tồn tại trong danh sách nhân viên.")
            emp_id = self._next_manual_id(cursor, "nhanvien")
            cursor.execute(
                """
                INSERT INTO nhanvien (id, idbdx, hoten, diachi, ngaysinh, chucvu, sdt, ngaybatdau, email, cccd)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    emp_id,
                    lot_id,
                    clean_name,
                    clean_addr,
                    birth_date.strftime("%Y-%m-%d"),
                    clean_role,
                    clean_phone,
                    start_date.strftime("%Y-%m-%d"),
                    clean_email,
                    clean_cccd,
                ),
            )
        return emp_id

    def update_employee(
        self,
        emp_id: int,
        lot_id: Optional[int],
        full_name: str,
        address: str,
        role: str,
        phone: str,
        email: str,
        cccd: str,
    ) -> None:
        """Update employee profile and role."""
        clean_name = self._require_text(full_name, "Họ tên", 30)
        clean_addr = self._require_text(address, "Địa chỉ", 50)
        clean_role = self._require_text(role, "Chức vụ", 10)
        clean_phone = self._require_text(phone, "Số điện thoại", 10)
        clean_email = self._require_text(email, "Email", 30)
        clean_cccd = self._require_text(cccd, "CCCD", 15)

        dup = self.db.fetch_one(
            "SELECT id FROM nhanvien WHERE cccd = %s AND id <> %s LIMIT 1",
            (clean_cccd, emp_id),
        )
        if dup is not None:
            raise ValidationError(f"CCCD {clean_cccd} đã thuộc về nhân viên khác.")

        self.db.execute_non_query(
            """
            UPDATE nhanvien
            SET idbdx = %s, hoten = %s, diachi = %s, chucvu = %s, sdt = %s, email = %s, cccd = %s
            WHERE id = %s
            """,
            (lot_id, clean_name, clean_addr, clean_role, clean_phone, clean_email, clean_cccd, emp_id),
        )

    def delete_employee(self, emp_id: int) -> None:
        """Delete an employee if they have no associated turns or payments."""
        if self.db.fetch_one("SELECT id FROM luotdo WHERE idnv = %s LIMIT 1", (emp_id,)) is not None:
            raise ValidationError("Nhân viên đã ghi nhận lượt đỗ, không thể xóa.")
        if self.db.fetch_one("SELECT id FROM thanhtoan WHERE idnv = %s LIMIT 1", (emp_id,)) is not None:
            raise ValidationError("Nhân viên đã ghi nhận thanh toán, không thể xóa.")
        self.db.execute_non_query("DELETE FROM nhanvien WHERE id = %s", (emp_id,))

    # ------------------------------------------------------------------
    # CRUD: Cards, Customers & Vehicles
    # ------------------------------------------------------------------

    def create_card(self, code: str) -> int:
        """Issue a new RFID parking card with transaction-safe ID allocation."""
        clean_code = self._require_text(code, "Mã thẻ", 10)
        with self.db.transaction() as cursor:
            cursor.execute("SELECT id FROM thexe WHERE maso = %s LIMIT 1", (clean_code,))
            if cursor.fetchone() is not None:
                raise ValidationError(f"Mã thẻ '{clean_code}' đã tồn tại.")
            card_id = self._next_manual_id(cursor, "thexe")
            cursor.execute(
                "INSERT INTO thexe (id, maso, trangthai) VALUES (%s, %s, 1)",
                (card_id, clean_code),
            )
        return card_id

    def set_card_status(self, card_id: int, status: int) -> None:
        """Set card status between available (1) and lost/damaged (2)."""
        if status not in (1, 2):
            raise ValidationError("Trạng thái thẻ chỉ nhận 1 (Sẵn sàng) hoặc 2 (Mất / Hỏng).")
        with self.db.transaction() as cursor:
            cursor.execute("SELECT id, trangthai FROM thexe WHERE id = %s FOR UPDATE", (card_id,))
            card = cursor.fetchone()
            if card is None:
                raise ValidationError("Thẻ xe không tồn tại.")
            if int(card["trangthai"]) == 0:
                raise ValidationError("Thẻ đang gắn với xe trong bãi, không thể đổi trạng thái trực tiếp.")
            cursor.execute("UPDATE thexe SET trangthai = %s WHERE id = %s", (status, card_id))

    def delete_card(self, card_id: int) -> None:
        """Delete an unused card that has no turn or monthly pass history."""
        with self.db.transaction() as cursor:
            cursor.execute("SELECT id, trangthai FROM thexe WHERE id = %s FOR UPDATE", (card_id,))
            card = cursor.fetchone()
            if card is None:
                raise ValidationError("Thẻ xe không tồn tại.")
            if int(card["trangthai"]) == 0:
                raise ValidationError("Thẻ đang được sử dụng, không thể xóa.")
            cursor.execute("SELECT id FROM luotdo WHERE idtx = %s LIMIT 1", (card_id,))
            if cursor.fetchone() is not None:
                raise ValidationError("Thẻ đã có lịch sử lượt đỗ, chỉ có thể khóa Mất / Hỏng.")
            cursor.execute("SELECT id FROM vethang WHERE idtx = %s LIMIT 1", (card_id,))
            if cursor.fetchone() is not None:
                raise ValidationError("Thẻ đang/đã gắn với vé tháng, không thể xóa.")
            cursor.execute("DELETE FROM thexe WHERE id = %s", (card_id,))

    def update_customer(
        self,
        customer_id: int,
        full_name: str,
        phone: str,
        cccd: str,
        customer_type_id: int,
    ) -> None:
        """Update customer profile."""
        clean_name = self._require_text(full_name, "Họ tên khách hàng", 30)
        clean_phone = self._require_text(phone, "Số điện thoại", 20)
        clean_cccd = self._require_text(cccd, "CCCD", 15)
        dup = self.db.fetch_one(
            "SELECT id FROM khachhang WHERE cccd = %s AND id <> %s LIMIT 1",
            (clean_cccd, customer_id),
        )
        if dup is not None:
            raise ValidationError(f"CCCD {clean_cccd} đã thuộc về khách hàng khác.")
        self.db.execute_non_query(
            """
            UPDATE khachhang
            SET hoten = %s, sdt = %s, cccd = %s, idlkh = %s
            WHERE id = %s
            """,
            (clean_name, clean_phone, clean_cccd, customer_type_id, customer_id),
        )

    def delete_customer(self, customer_id: int) -> None:
        """Delete a customer if they have no monthly passes."""
        if self.db.fetch_one("SELECT id FROM vethang WHERE idkh = %s LIMIT 1", (customer_id,)) is not None:
            raise ValidationError("Khách hàng đã có lịch sử vé tháng, không thể xóa.")
        self.db.execute_non_query("DELETE FROM khachhang WHERE id = %s", (customer_id,))

    def update_vehicle(self, vehicle_id: int, plate: str, vehicle_type_id: int) -> None:
        """Update license plate and vehicle type."""
        clean_plate = self._normalize_plate(plate)
        dup = self.db.fetch_one(
            "SELECT id FROM phuongtien WHERE bienso = %s AND id <> %s LIMIT 1",
            (clean_plate, vehicle_id),
        )
        if dup is not None:
            raise ValidationError(f"Biển số {clean_plate} đã tồn tại.")
        self.db.execute_non_query(
            "UPDATE phuongtien SET bienso = %s, idlpt = %s WHERE id = %s",
            (clean_plate, vehicle_type_id, vehicle_id),
        )

    def delete_vehicle(self, vehicle_id: int) -> None:
        """Delete a vehicle if it has no turns or monthly passes."""
        if self.db.fetch_one("SELECT id FROM luotdo WHERE idpt = %s LIMIT 1", (vehicle_id,)) is not None:
            raise ValidationError("Phương tiện đã có lịch sử lượt đỗ, không thể xóa.")
        if self.db.fetch_one("SELECT id FROM vethang WHERE idpt = %s LIMIT 1", (vehicle_id,)) is not None:
            raise ValidationError("Phương tiện đã gắn với vé tháng, không thể xóa.")
        self.db.execute_non_query("DELETE FROM phuongtien WHERE id = %s", (vehicle_id,))

    # ------------------------------------------------------------------
    # Monthly Pass Lifecycle & Operational Exceptions
    # ------------------------------------------------------------------

    def renew_monthly_pass(
        self,
        pass_id: int,
        months: int,
        employee_id: Optional[int] = None,
        payment_method: str = "Tiền mặt",
    ) -> dict[str, Any]:
        """Extend an existing monthly pass by N 30-day periods and optionally record payment."""
        if months <= 0 or months > 24:
            raise ValidationError("Số tháng gia hạn phải từ 1 đến 24.")
        with self.db.transaction() as cursor:
            cursor.execute(
                """
                SELECT vt.id, vt.ngayketthuc, bg.dongia
                FROM vethang vt
                LEFT JOIN banggia bg ON bg.id = vt.idbg
                WHERE vt.id = %s
                FOR UPDATE
                """,
                (pass_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValidationError("Không tìm thấy vé tháng.")
            end_dt = row["ngayketthuc"]
            if isinstance(end_dt, str):
                end_dt = date.fromisoformat(end_dt)
            elif isinstance(end_dt, datetime):
                end_dt = end_dt.date()
            base_date = max(end_dt, date.today())
            new_end = base_date + timedelta(days=30 * months)
            cursor.execute(
                "UPDATE vethang SET ngayketthuc = %s WHERE id = %s",
                (new_end.strftime("%Y-%m-%d"), pass_id),
            )
            amount = int(row.get("dongia") or 0) * months
            if employee_id is not None:
                cursor.execute(
                    """
                    INSERT INTO thanhtoan (idld, chiphi, giothanhtoan, trangthai, idnv, loaithanhtoan, idvt)
                    VALUES (NULL, %s, NOW(), 'Thành công', %s, %s, %s)
                    """,
                    (amount, employee_id, payment_method, pass_id),
                )
        return {"pass_id": pass_id, "new_end_date": new_end, "amount": amount}

    def update_monthly_pass_assets(
        self,
        pass_id: int,
        plate: str,
        vehicle_type_id: int,
        new_card_id: int,
    ) -> None:
        """Reassign vehicle plate or RFID card for an existing monthly pass."""
        clean_plate = self._normalize_plate(plate)
        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT id, idtx FROM vethang WHERE id = %s FOR UPDATE",
                (pass_id,),
            )
            pass_row = cursor.fetchone()
            if pass_row is None:
                raise ValidationError("Không tìm thấy vé tháng.")

            cursor.execute("SELECT id, idlpt FROM phuongtien WHERE bienso = %s LIMIT 1", (clean_plate,))
            veh_row = cursor.fetchone()
            if veh_row:
                vehicle_id = int(veh_row["id"])
            else:
                cursor.execute(
                    "INSERT INTO phuongtien (bienso, idlpt) VALUES (%s, %s)",
                    (clean_plate, vehicle_type_id),
                )
                vehicle_id = int(cursor.lastrowid)

            if int(new_card_id) != int(pass_row["idtx"]):
                cursor.execute(
                    "SELECT id, trangthai FROM thexe WHERE id = %s FOR UPDATE",
                    (new_card_id,),
                )
                card = cursor.fetchone()
                if card is None or int(card["trangthai"]) != 1:
                    raise ValidationError("Thẻ mới không ở trạng thái sẵn sàng.")
                cursor.execute(
                    """
                    SELECT id FROM vethang
                    WHERE idtx = %s AND ngayketthuc >= CURDATE() AND id <> %s
                    LIMIT 1
                    """,
                    (new_card_id, pass_id),
                )
                if cursor.fetchone() is not None:
                    raise ValidationError("Thẻ mới đang được gắn với một vé tháng khác còn hiệu lực.")

            cursor.execute(
                "UPDATE vethang SET idpt = %s, idtx = %s WHERE id = %s",
                (vehicle_id, new_card_id, pass_id),
            )

    def cancel_monthly_pass(self, pass_id: int) -> None:
        """Expire a monthly pass early by setting ngayketthuc to yesterday."""
        yesterday = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT id, idtx, ngayketthuc FROM vethang WHERE id = %s FOR UPDATE",
                (pass_id,),
            )
            row = cursor.fetchone()
            if row is None:
                raise ValidationError("Không tìm thấy vé tháng.")
            cursor.execute(
                "UPDATE vethang SET ngayketthuc = %s WHERE id = %s",
                (yesterday, pass_id),
            )
            cursor.execute(
                """
                SELECT id FROM luotdo
                WHERE idtx = %s
                  AND NOT EXISTS (SELECT 1 FROM thanhtoan tt WHERE tt.idld = luotdo.id)
                LIMIT 1
                """,
                (row["idtx"],),
            )
            if cursor.fetchone() is None:
                cursor.execute(
                    "UPDATE thexe SET trangthai = 1 WHERE id = %s AND trangthai = 0",
                    (row["idtx"],),
                )

    def get_monthly_pass_revenue_summary(self) -> dict[str, Any]:
        """Aggregate monthly pass revenue directly from vethang joined with banggia."""
        row = self.db.fetch_one(
            """
            SELECT
                COUNT(*) AS total_passes,
                COALESCE(SUM(CASE WHEN vt.ngaybatdau <= CURDATE() AND vt.ngayketthuc >= CURDATE() THEN 1 ELSE 0 END), 0) AS active_passes,
                COALESCE(SUM(COALESCE(bg.dongia, 0)), 0) AS total_pass_revenue,
                COALESCE(SUM(CASE WHEN YEAR(vt.ngaybatdau) = YEAR(CURDATE()) AND MONTH(vt.ngaybatdau) = MONTH(CURDATE()) THEN COALESCE(bg.dongia, 0) ELSE 0 END), 0) AS this_month_pass_revenue
            FROM vethang vt
            LEFT JOIN banggia bg ON bg.id = vt.idbg
            """
        ) or {}
        return {
            "total_passes": int(row.get("total_passes") or 0),
            "active_passes": int(row.get("active_passes") or 0),
            "total_pass_revenue": int(row.get("total_pass_revenue") or 0),
            "this_month_pass_revenue": int(row.get("this_month_pass_revenue") or 0),
        }

    def move_active_turn_slot(self, turn_id: int, new_slot_id: int) -> None:
        """Move an active parked vehicle from its current slot to another free slot."""
        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT id, idvtd FROM luotdo WHERE id = %s FOR UPDATE",
                (turn_id,),
            )
            turn = cursor.fetchone()
            if turn is None:
                raise ValidationError("Lượt đỗ không tồn tại.")
            cursor.execute("SELECT id FROM thanhtoan WHERE idld = %s LIMIT 1", (turn_id,))
            if cursor.fetchone() is not None:
                raise ValidationError("Lượt đỗ đã thanh toán, không thể chuyển vị trí.")

            old_slot_id = int(turn["idvtd"])
            if old_slot_id == int(new_slot_id):
                raise ValidationError("Vị trí mới trùng với vị trí hiện tại.")

            cursor.execute("SELECT id, trangthai FROM vitrido WHERE id = %s FOR UPDATE", (new_slot_id,))
            new_slot = cursor.fetchone()
            if new_slot is None or int(new_slot["trangthai"]) != 1:
                raise ValidationError("Vị trí đích không trống hoặc đang bảo trì.")

            cursor.execute("UPDATE vitrido SET trangthai = 1 WHERE id = %s", (old_slot_id,))
            cursor.execute("UPDATE vitrido SET trangthai = 0 WHERE id = %s", (new_slot_id,))
            cursor.execute("UPDATE luotdo SET idvtd = %s WHERE id = %s", (new_slot_id, turn_id))

    def cancel_active_turn(self, turn_id: int) -> None:
        """Cancel an unpaid active turn created by mistake and release slot & card."""
        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT id, idvtd, idtx FROM luotdo WHERE id = %s FOR UPDATE",
                (turn_id,),
            )
            turn = cursor.fetchone()
            if turn is None:
                raise ValidationError("Lượt đỗ không tồn tại.")
            cursor.execute("SELECT id FROM thanhtoan WHERE idld = %s LIMIT 1", (turn_id,))
            if cursor.fetchone() is not None:
                raise ValidationError("Lượt đỗ đã có giao dịch thanh toán, không thể hủy.")

            cursor.execute("UPDATE vitrido SET trangthai = 1 WHERE id = %s AND trangthai = 0", (turn["idvtd"],))
            cursor.execute("UPDATE thexe SET trangthai = 1 WHERE id = %s AND trangthai = 0", (turn["idtx"],))
            cursor.execute("DELETE FROM luotdo WHERE id = %s", (turn_id,))

    def update_payment_status(self, payment_id: int, new_status: str) -> None:
        """Update payment transaction status (e.g. refund or failure handling)."""
        allowed = ("Thành công", "Hoàn tiền", "Thất bại")
        cleaned = new_status.strip()
        if cleaned not in allowed:
            raise ValidationError(f"Trạng thái giao dịch chỉ hỗ trợ: {', '.join(allowed)}.")
        self.db.execute_non_query(
            "UPDATE thanhtoan SET trangthai = %s WHERE id = %s",
            (cleaned, payment_id),
        )

    # ------------------------------------------------------------------
    # Printable Ticket & Receipt HTML Builders
    # ------------------------------------------------------------------

    @staticmethod
    def build_ticket_html(
        turn_id: int,
        plate: str,
        vehicle_type: str,
        slot_label: str,
        card_code: str,
        checkin_time: str,
    ) -> str:
        """Generate a printable HTML parking ticket for check-in."""
        return (
            "<!DOCTYPE html><html lang='vi'><head><meta charset='utf-8'>"
            "<title>Phiếu gửi xe</title>"
            "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:340px;margin:24px auto;"
            "border:1px dashed #334155;padding:16px;border-radius:8px}h2{margin:0 0 8px;font-size:16px;text-align:center}"
            ".row{display:flex;justify-content:space-between;margin:6px 0;font-size:13px}"
            ".plate{font-size:20px;font-weight:700;text-align:center;margin:10px 0;letter-spacing:1px}</style></head><body>"
            "<h2>PHIẾU GỬI XE — PTIT</h2>"
            f"<div class='plate'>{html.escape(plate)}</div>"
            f"<div class='row'><span>Mã lượt:</span><strong>#{turn_id}</strong></div>"
            f"<div class='row'><span>Loại xe:</span><span>{html.escape(vehicle_type)}</span></div>"
            f"<div class='row'><span>Vị trí đỗ:</span><span>{html.escape(slot_label)}</span></div>"
            f"<div class='row'><span>Mã thẻ:</span><span>{html.escape(card_code)}</span></div>"
            f"<div class='row'><span>Giờ vào:</span><span>{html.escape(checkin_time)}</span></div>"
            "<hr><p style='text-align:center;font-size:11px;color:#64748b'>Vui lòng giữ phiếu/thẻ khi lấy xe.</p>"
            "</body></html>"
        )

    @staticmethod
    def build_receipt_html(
        receipt_id: int,
        plate: str,
        ticket_type: str,
        checkin_time: str,
        checkout_time: str,
        amount: int,
        status: str = "Thành công",
    ) -> str:
        """Generate a printable HTML payment receipt for check-out or history."""
        return (
            "<!DOCTYPE html><html lang='vi'><head><meta charset='utf-8'>"
            "<title>Biên lai thu phí</title>"
            "<style>body{font-family:Segoe UI,Arial,sans-serif;max-width:360px;margin:24px auto;"
            "border:1px solid #cbd5e1;padding:18px;border-radius:8px}h2{margin:0 0 10px;font-size:16px;text-align:center}"
            ".row{display:flex;justify-content:space-between;margin:6px 0;font-size:13px}"
            ".total{font-size:18px;font-weight:700;color:#0f172a;border-top:1px dashed #94a3b8;padding-top:8px;margin-top:10px}</style></head><body>"
            "<h2>BIÊN LAI THU PHÍ ĐỖ XE — PTIT</h2>"
            f"<div class='row'><span>Mã giao dịch / lượt:</span><strong>#{receipt_id}</strong></div>"
            f"<div class='row'><span>Biển số:</span><strong>{html.escape(plate)}</strong></div>"
            f"<div class='row'><span>Loại vé:</span><span>{html.escape(ticket_type)}</span></div>"
            f"<div class='row'><span>Giờ vào:</span><span>{html.escape(checkin_time)}</span></div>"
            f"<div class='row'><span>Giờ ra / TT:</span><span>{html.escape(checkout_time)}</span></div>"
            f"<div class='row'><span>Trạng thái:</span><span>{html.escape(status)}</span></div>"
            f"<div class='row total'><span>Tổng thu:</span><span>{amount:,} VNĐ</span></div>"
            "</body></html>"
        )

    # ------------------------------------------------------------------
    # Maintenance (Idempotent)
    # ------------------------------------------------------------------

    def reconcile_slot_states(self) -> None:
        """Reset orphaned occupied slots (trangthai = 0 with no active turn) to free."""
        self.db.execute_non_query(
            """
            UPDATE vitrido v
            SET v.trangthai = 1
            WHERE v.trangthai = 0
              AND NOT EXISTS (
                  SELECT 1
                  FROM luotdo ld
                  WHERE ld.idvtd = v.id
                    AND NOT EXISTS (
                        SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id
                    )
              )
            """
        )

    # ------------------------------------------------------------------
    # Audit Logs, Shift Handover & Operational Alerts
    # ------------------------------------------------------------------

    def record_audit_log(
        self,
        actor_id: Optional[int],
        actor_username: str,
        action: str,
        entity_type: str,
        entity_id: Optional[Any] = None,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        """Persist an immutable audit trail entry for sensitive actions."""
        payload = json.dumps(details or {}, ensure_ascii=False, default=str)
        self.db.execute_non_query(
            """
            INSERT INTO audit_logs (actor_id, actor_username, action, entity_type, entity_id, details_json)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (
                actor_id,
                (actor_username or "system")[:50],
                action[:60],
                entity_type[:40],
                str(entity_id)[:64] if entity_id is not None else None,
                payload,
            ),
        )

    def get_audit_logs(self, limit: int = 100) -> list[dict[str, Any]]:
        """Retrieve recent audit trail entries."""
        return self.db.fetch_all(
            """
            SELECT id, actor_id, actor_username, action, entity_type, entity_id, details_json, created_at
            FROM audit_logs
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,),
        )

    def get_active_shift(self, employee_id: int) -> Optional[dict[str, Any]]:
        """Return the currently open shift for an employee with live totals."""
        shift = self.db.fetch_one(
            """
            SELECT ca.*, nv.hoten AS ten_nhanvien, bdx.tenbaido
            FROM ca_lam_viec ca
            JOIN nhanvien nv ON nv.id = ca.idnv
            LEFT JOIN baidoxe bdx ON bdx.id = ca.idbdx
            WHERE ca.idnv = %s AND ca.status = 'OPEN'
            ORDER BY ca.id DESC
            LIMIT 1
            """,
            (employee_id,),
        )
        if not shift:
            return None
        totals = self.db.fetch_one(
            """
            SELECT
                COUNT(*) AS tx_count,
                COALESCE(SUM(CASE WHEN loaithanhtoan = 'Tiền mặt' THEN chiphi ELSE 0 END), 0) AS cash_total,
                COALESCE(SUM(CASE WHEN loaithanhtoan <> 'Tiền mặt' THEN chiphi ELSE 0 END), 0) AS transfer_total
            FROM thanhtoan
            WHERE idnv = %s
              AND trangthai = 'Thành công'
              AND giothanhtoan >= %s
            """,
            (employee_id, shift["started_at"]),
        ) or {}
        shift["live_tx_count"] = int(totals.get("tx_count") or 0)
        shift["live_cash_total"] = int(totals.get("cash_total") or 0)
        shift["live_transfer_total"] = int(totals.get("transfer_total") or 0)
        shift["live_expected_cash"] = int(shift.get("opening_cash") or 0) + shift["live_cash_total"]
        return shift

    def open_shift(
        self,
        employee_id: int,
        lot_id: Optional[int],
        opening_cash: int = 0,
        note: str = "",
    ) -> int:
        """Open a new cashier/operator shift if none is currently open."""
        if opening_cash < 0:
            raise ValidationError("Tiền đầu ca không được âm.")
        existing = self.db.fetch_one(
            "SELECT id FROM ca_lam_viec WHERE idnv = %s AND status = 'OPEN' LIMIT 1",
            (employee_id,),
        )
        if existing:
            raise ValidationError("Nhân viên đang có một ca làm việc chưa đóng.")
        return self.db.execute_non_query(
            """
            INSERT INTO ca_lam_viec (idnv, idbdx, opening_cash, note, status)
            VALUES (%s, %s, %s, %s, 'OPEN')
            """,
            (employee_id, lot_id, opening_cash, note.strip()[:255] or None),
        )

    def close_shift(
        self,
        shift_id: int,
        employee_id: int,
        actual_cash: int,
        note: str = "",
    ) -> dict[str, Any]:
        """Close an open shift and compute expected vs actual cash."""
        if actual_cash < 0:
            raise ValidationError("Tiền bàn giao thực tế không được âm.")
        with self.db.transaction() as cursor:
            cursor.execute(
                "SELECT * FROM ca_lam_viec WHERE id = %s AND idnv = %s FOR UPDATE",
                (shift_id, employee_id),
            )
            shift = cursor.fetchone()
            if not shift:
                raise ValidationError("Không tìm thấy ca làm việc.")
            if shift["status"] != "OPEN":
                raise ValidationError("Ca làm việc này đã được đóng trước đó.")

            cursor.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN loaithanhtoan = 'Tiền mặt' THEN chiphi ELSE 0 END), 0) AS cash_total,
                    COALESCE(SUM(CASE WHEN loaithanhtoan <> 'Tiền mặt' THEN chiphi ELSE 0 END), 0) AS transfer_total
                FROM thanhtoan
                WHERE idnv = %s
                  AND trangthai = 'Thành công'
                  AND giothanhtoan >= %s
                """,
                (employee_id, shift["started_at"]),
            )
            totals = cursor.fetchone() or {}
            cash_total = int(totals.get("cash_total") or 0)
            transfer_total = int(totals.get("transfer_total") or 0)
            expected_cash = int(shift.get("opening_cash") or 0) + cash_total

            cursor.execute(
                """
                UPDATE ca_lam_viec
                SET ended_at = NOW(),
                    expected_cash = %s,
                    actual_cash = %s,
                    transfer_total = %s,
                    note = COALESCE(NULLIF(%s, ''), note),
                    status = 'CLOSED'
                WHERE id = %s
                """,
                (expected_cash, actual_cash, transfer_total, note.strip()[:255], shift_id),
            )
        return {
            "shift_id": shift_id,
            "expected_cash": expected_cash,
            "actual_cash": actual_cash,
            "transfer_total": transfer_total,
            "diff": actual_cash - expected_cash,
        }

    def get_shifts(self, limit: int = 50) -> list[dict[str, Any]]:
        """List recent cashier/operator shifts."""
        return self.db.fetch_all(
            """
            SELECT ca.*, nv.hoten AS ten_nhanvien, bdx.tenbaido
            FROM ca_lam_viec ca
            JOIN nhanvien nv ON nv.id = ca.idnv
            LEFT JOIN baidoxe bdx ON bdx.id = ca.idbdx
            ORDER BY ca.id DESC
            LIMIT %s
            """,
            (limit,),
        )

    def get_operational_alerts(
        self,
        overdue_hours: int = 24,
        pass_expiring_days: int = 7,
    ) -> dict[str, Any]:
        """Return active operational alerts: overdue vehicles, expiring passes, lost cards."""
        overdue_turns = self.db.fetch_all(
            """
            SELECT ld.id, pt.bienso, tx.maso AS ma_the, bdx.tenbaido,
                   kvd.ten AS khu_vuc, vtd.sothutu, ld.giovao,
                   TIMESTAMPDIFF(HOUR, ld.giovao, NOW()) AS hours_parked
            FROM luotdo ld
            JOIN phuongtien pt ON pt.id = ld.idpt
            JOIN thexe tx ON tx.id = ld.idtx
            JOIN vitrido vtd ON vtd.id = ld.idvtd
            JOIN khuvucdo kvd ON kvd.id = vtd.idkvd
            JOIN baidoxe bdx ON bdx.id = kvd.idbdx
            WHERE NOT EXISTS (SELECT 1 FROM thanhtoan tt WHERE tt.idld = ld.id)
              AND TIMESTAMPDIFF(HOUR, ld.giovao, NOW()) >= %s
            ORDER BY ld.giovao ASC
            """,
            (overdue_hours,),
        )
        expiring_passes = self.db.fetch_all(
            """
            SELECT vt.id, kh.hoten AS ten_khachhang, kh.sdt, pt.bienso,
                   tx.maso AS ma_the, vt.ngayketthuc,
                   DATEDIFF(vt.ngayketthuc, CURDATE()) AS days_left
            FROM vethang vt
            JOIN khachhang kh ON kh.id = vt.idkh
            JOIN phuongtien pt ON pt.id = vt.idpt
            JOIN thexe tx ON tx.id = vt.idtx
            WHERE vt.ngayketthuc BETWEEN CURDATE() AND DATE_ADD(CURDATE(), INTERVAL %s DAY)
            ORDER BY vt.ngayketthuc ASC
            """,
            (pass_expiring_days,),
        )
        lost_cards = self.db.fetch_all(
            "SELECT id, maso FROM thexe WHERE trangthai = 2 ORDER BY id DESC"
        )
        return {
            "overdue_turns": overdue_turns,
            "expiring_passes": expiring_passes,
            "lost_cards": lost_cards,
        }
