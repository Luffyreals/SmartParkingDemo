from __future__ import annotations

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
                COALESCE(SUM(CASE WHEN v.trangthai = 0 THEN 1 ELSE 0 END), 0) AS dang_do
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
                COALESCE(SUM(CASE WHEN v.trangthai = 0 THEN 1 ELSE 0 END), 0) AS dang_do
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

    def check_out_vehicle(self, turn_id: int, employee_id: int) -> FeeQuote:
        """Complete parking turn, record payment, and free slot & card atomically."""
        quote = self.get_fee_quote(turn_id)
        now_str = quote.checkout_time.strftime("%Y-%m-%d %H:%M:%S")

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
                    quote.amount,
                    now_str,
                    employee_id,
                    1 if quote.is_monthly_pass else 0,
                    quote.monthly_pass_id,
                ),
            )
            cursor.execute(
                "UPDATE vitrido SET trangthai = 1 WHERE id = %s",
                (turn["idvtd"],),
            )
            cursor.execute(
                "UPDATE thexe SET trangthai = 1 WHERE id = %s",
                (turn["idtx"],),
            )

        return quote

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
                pt.bienso,
                lpt.tenloai AS loaiphuongtien,
                tx.maso AS mathe,
                b.tenbaido,
                CONCAT(k.ten, '-', v.sothutu) AS vitri,
                ld.giovao,
                ld.giora,
                tt.giothanhtoan,
                tt.chiphi,
                CASE WHEN tt.loaithanhtoan = 1 THEN 'Vé tháng' ELSE 'Vé ngày' END AS hinhthuc,
                tt.idvt AS ma_ve_thang,
                tt.trangthai,
                nv_in.hoten AS nv_tiep_nhan,
                nv.hoten AS nhanvien
            FROM thanhtoan tt
            JOIN luotdo ld ON ld.id = tt.idld
            JOIN vitrido v ON v.id = ld.idvtd
            JOIN khuvucdo k ON k.id = v.idkvd
            JOIN baidoxe b ON b.id = k.idbdx
            JOIN nhanvien nv ON nv.id = tt.idnv
            LEFT JOIN nhanvien nv_in ON nv_in.id = ld.idnv
            LEFT JOIN thexe tx ON tx.id = ld.idtx
            LEFT JOIN phuongtien pt ON pt.id = ld.idpt
            LEFT JOIN loaiphuongtien lpt ON lpt.id = pt.idlpt
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
    ) -> int:
        """Register or renew a monthly parking pass for a customer and vehicle."""
        hoten_clean = hoten.strip()
        sdt_clean = sdt.strip()
        cccd_clean = cccd.strip()
        if not hoten_clean or len(hoten_clean) > 20:
            raise ValidationError("Họ tên khách hàng phải từ 1 đến 20 ký tự.")
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
                SELECT id FROM banggia
                WHERE loaive = 'tháng' AND idlpt = %s AND idlkh = %s
                LIMIT 1
                """,
                (vehicle_type_id, customer_type_id),
            )
            tariff = cursor.fetchone()
            if tariff is None:
                raise ValidationError("Không tìm thấy đơn giá vé tháng cho cấu hình này.")

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
            return int(cursor.lastrowid)

    # ------------------------------------------------------------------
    # Demo Data Seeder & Maintenance (Idempotent)
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

    def seed_demo_data(self) -> dict[str, int]:
        """Populate sample operational records if transactional tables are empty."""
        self.reconcile_slot_states()
        summary = {"slots_added": 0, "employees_added": 0, "cards_added": 0, "turns_added": 0}

        # 1. Ensure slots exist across all 3 lots (auto lot already has 5 in zone 1)
        slot_count_row = self.db.fetch_one("SELECT COUNT(*) AS cnt FROM vitrido")
        if int((slot_count_row or {}).get("cnt") or 0) <= 5:
            # Zone 11 = Lot 2 (Xe máy) Khu A; Zone 31 = Lot 3 (Xe đạp) Khu A
            for zone_id, qty in [(2, 5), (11, 10), (12, 10), (31, 6)]:
                existing_zone = self.db.fetch_one(
                    "SELECT COUNT(*) AS cnt FROM vitrido WHERE idkvd = %s",
                    (zone_id,),
                )
                if int((existing_zone or {}).get("cnt") or 0) == 0:
                    summary["slots_added"] += self.add_slots_to_zone(zone_id, qty)

        # 2. Seed employees if empty
        if int((self.db.fetch_one("SELECT COUNT(*) AS cnt FROM nhanvien") or {}).get("cnt") or 0) == 0:
            employees = [
                (1, "Nguyễn Văn An", "Hà Đông, HN", "1995-03-12", "Bảo vệ", "0912345671", "2024-01-10", "an@ptit.edu.vn", "001095000111"),
                (2, "Trần Thị Bình", "Thanh Xuân, HN", "1998-07-22", "Thu ngân", "0912345672", "2024-03-01", "binh@ptit.edu.vn", "001098000222"),
                (3, "Lê Minh Cường", "Cầu Giấy, HN", "1992-11-05", "Quản lý", "0912345673", "2023-09-15", "cuong@ptit.edu.vn", "001092000333"),
            ]
            for emp in employees:
                self.db.execute_non_query(
                    """
                    INSERT INTO nhanvien (idbdx, hoten, diachi, ngaysinh, chucvu, sdt, ngaybatdau, email, cccd)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    emp,
                )
                summary["employees_added"] += 1

        # 3. Seed parking cards if empty
        if int((self.db.fetch_one("SELECT COUNT(*) AS cnt FROM thexe") or {}).get("cnt") or 0) == 0:
            for i in range(1, 16):
                self.db.execute_non_query(
                    "INSERT INTO thexe (maso, trangthai) VALUES (%s, 1)",
                    (f"PTIT{i:03d}",),
                )
                summary["cards_added"] += 1

        # 4. Seed sample completed & active turns if luotdo is empty
        if int((self.db.fetch_one("SELECT COUNT(*) AS cnt FROM luotdo") or {}).get("cnt") or 0) == 0:
            emp = self.db.fetch_one("SELECT id FROM nhanvien ORDER BY id LIMIT 1")
            emp_id = int(emp["id"]) if emp else 1

            # Sample vehicles
            sample_vehicles = [
                ("30A12345", 3),
                ("29B56789", 2),
                ("29C99887", 2),
                ("XD0012", 1),
                ("30G45678", 3),
            ]
            vehicle_ids: list[tuple[int, int, str]] = []
            for plate, lpt_id in sample_vehicles:
                existing_v = self.db.fetch_one("SELECT id FROM phuongtien WHERE bienso = %s", (plate,))
                if existing_v:
                    vid = int(existing_v["id"])
                else:
                    vid = self.db.execute_non_query(
                        "INSERT INTO phuongtien (bienso, idlpt) VALUES (%s, %s)",
                        (plate, lpt_id),
                    )
                vehicle_ids.append((vid, lpt_id, plate))

            cards = self.get_cards(only_available=True)
            now = datetime.now()

            # 4 completed historical turns across recent days
            history_specs = [
                (vehicle_ids[0], 1, 3, 10000, now - timedelta(days=3, hours=5), now - timedelta(days=3, hours=1)),
                (vehicle_ids[1], 11, 2, 5000, now - timedelta(days=2, hours=6), now - timedelta(days=2, hours=2)),
                (vehicle_ids[2], 12, 2, 5000, now - timedelta(days=1, hours=4), now - timedelta(days=1, hours=1)),
                (vehicle_ids[3], 31, 1, 3000, now - timedelta(hours=6), now - timedelta(hours=2)),
            ]
            for idx, (veh, zone_hint, tariff_id, fee, t_in, t_out) in enumerate(history_specs):
                slot_row = self.db.fetch_one(
                    "SELECT id FROM vitrido WHERE idkvd = %s AND trangthai = 1 ORDER BY id LIMIT 1",
                    (zone_hint,),
                ) or self.db.fetch_one("SELECT id FROM vitrido WHERE trangthai = 1 ORDER BY id LIMIT 1")
                if slot_row and idx < len(cards):
                    turn_id = self.db.execute_non_query(
                        """
                        INSERT INTO luotdo (idvtd, giovao, giora, idnv, idpt, idtx, idbg)
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                        """,
                        (
                            int(slot_row["id"]),
                            t_in.strftime("%Y-%m-%d %H:%M:%S"),
                            t_out.strftime("%Y-%m-%d %H:%M:%S"),
                            emp_id,
                            veh[0],
                            int(cards[idx]["id"]),
                            tariff_id,
                        ),
                    )
                    self.db.execute_non_query(
                        """
                        INSERT INTO thanhtoan (idld, chiphi, giothanhtoan, trangthai, idnv, loaithanhtoan, idvt)
                        VALUES (%s, %s, %s, 'Thành công', %s, 0, NULL)
                        """,
                        (turn_id, fee, t_out.strftime("%Y-%m-%d %H:%M:%S"), emp_id),
                    )
                    summary["turns_added"] += 1

            # 2 active turns currently parked
            active_specs = [
                (vehicle_ids[4][2], 3, 1, cards[5]["id"] if len(cards) > 5 else cards[0]["id"]),
                (vehicle_ids[1][2], 2, 11, cards[6]["id"] if len(cards) > 6 else cards[1]["id"]),
            ]
            for plate, lpt_id, zone_hint, card_id in active_specs:
                slot_row = self.db.fetch_one(
                    "SELECT id FROM vitrido WHERE idkvd = %s AND trangthai = 1 ORDER BY id LIMIT 1",
                    (zone_hint,),
                )
                if slot_row:
                    try:
                        self.check_in_vehicle(plate, lpt_id, int(slot_row["id"]), int(card_id), emp_id)
                        summary["turns_added"] += 1
                    except ValidationError:
                        pass

        return summary
