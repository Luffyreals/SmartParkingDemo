import os
import sys
import unittest
from datetime import date, datetime, timedelta
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from services.db_service import DBService
from services.parking_service import ParkingService, ValidationError


class TestParkingService(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_db = MagicMock(spec=DBService)
        self.service = ParkingService(self.mock_db)

    def test_normalize_plate_valid(self) -> None:
        self.assertEqual(self.service._normalize_plate(" 29a 12345 "), "29A12345")

    def test_normalize_plate_empty_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.service._normalize_plate("   ")

    def test_normalize_plate_too_long_raises(self) -> None:
        with self.assertRaises(ValidationError):
            self.service._normalize_plate("29A-123456")

    def test_fee_quote_daily_ticket(self) -> None:
        checkin = datetime.now() - timedelta(hours=3)
        self.mock_db.fetch_one.side_effect = [
            {
                "id": 10,
                "giovao": checkin,
                "idpt": 5,
                "bienso": "29A12345",
                "loaiphuongtien": "xe máy",
                "loaive": "ngày",
                "dongia": 5000,
            },
            None,
        ]
        quote = self.service.get_fee_quote(10)
        self.assertEqual(quote.amount, 5000)
        self.assertFalse(quote.is_monthly_pass)
        self.assertEqual(quote.ticket_type, "Vé ngày")

    def test_fee_quote_monthly_pass_is_free(self) -> None:
        checkin = datetime.now() - timedelta(hours=5)
        self.mock_db.fetch_one.side_effect = [
            {
                "id": 11,
                "giovao": checkin,
                "idpt": 6,
                "bienso": "30A99999",
                "loaiphuongtien": "ô tô",
                "loaive": "tháng",
                "dongia": 240000,
            },
            {"id": 99},
        ]
        quote = self.service.get_fee_quote(11)
        self.assertEqual(quote.amount, 0)
        self.assertTrue(quote.is_monthly_pass)
        self.assertEqual(quote.monthly_pass_id, 99)

    def test_get_slots_query_deduplicates_active_turns(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_slots(lot_id=1)
        query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("ROW_NUMBER() OVER (PARTITION BY ld.idvtd", query)
        self.assertIn("WHERE rn = 1", query)

    def test_check_in_vehicle_rejects_occupied_slot_in_transaction(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.return_value = {"id": 1, "trangthai": 0}
        self.mock_db.transaction.return_value.__enter__.return_value = mock_cursor

        with self.assertRaises(ValidationError):
            self.service.check_in_vehicle("30G45678", 3, 1, 6, 1)

        self.assertEqual(mock_cursor.execute.call_count, 1)
        self.assertIn("FOR UPDATE", mock_cursor.execute.call_args[0][0])

    def test_check_in_vehicle_atomic_success(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"id": 1, "trangthai": 1},   # slot FOR UPDATE
            {"id": 6, "trangthai": 1},   # card FOR UPDATE
            None,                        # existing_active
            {"id": 7, "idlpt": 3},       # vehicle
            None,                        # monthly_pass
            {"id": 3},                   # daily tariff
        ]
        mock_cursor.rowcount = 1
        mock_cursor.lastrowid = 42
        self.mock_db.transaction.return_value.__enter__.return_value = mock_cursor

        turn_id = self.service.check_in_vehicle("30G45678", 3, 1, 6, 1)
        self.assertEqual(turn_id, 42)

    def test_check_out_vehicle_rejects_already_paid_in_transaction(self) -> None:
        checkin = datetime.now() - timedelta(hours=2)
        self.mock_db.fetch_one.side_effect = [
            {
                "id": 10,
                "giovao": checkin,
                "idpt": 5,
                "bienso": "29A12345",
                "loaiphuongtien": "xe máy",
                "loaive": "ngày",
                "dongia": 5000,
            },
            None,
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"id": 10, "idvtd": 1, "idtx": 2},  # luotdo FOR UPDATE
            {"id": 99},                          # existing thanhtoan
        ]
        self.mock_db.transaction.return_value.__enter__.return_value = mock_cursor

        with self.assertRaises(ValidationError):
            self.service.check_out_vehicle(10, 1)

        self.assertIn("FOR UPDATE", mock_cursor.execute.call_args_list[0][0][0])

    def test_check_out_vehicle_atomic_success(self) -> None:
        checkin = datetime.now() - timedelta(hours=2)
        self.mock_db.fetch_one.side_effect = [
            {
                "id": 10,
                "giovao": checkin,
                "idpt": 5,
                "bienso": "29A12345",
                "loaiphuongtien": "xe máy",
                "loaive": "ngày",
                "dongia": 5000,
            },
            None,
        ]
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"id": 10, "idvtd": 1, "idtx": 2},  # luotdo FOR UPDATE
            None,                                # no existing thanhtoan
        ]
        self.mock_db.transaction.return_value.__enter__.return_value = mock_cursor

        quote = self.service.check_out_vehicle(10, 1)
        self.assertEqual(quote.amount, 5000)
        self.assertEqual(mock_cursor.execute.call_count, 6)

    def test_register_monthly_pass_atomic_success(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"id": 4},                  # monthly tariff
            {"id": 3, "trangthai": 1},  # card is available
            None,                       # card not bound to another active pass
            None,                       # customer not found -> insert
            None,                       # vehicle not found -> insert
        ]
        mock_cursor.lastrowid = 77
        self.mock_db.transaction.return_value.__enter__.return_value = mock_cursor

        pass_id = self.service.register_monthly_pass(
            hoten="Nguyen Van Hoang Long 25",
            sdt="0912345678",
            cccd="001095000111",
            customer_type_id=1,
            license_plate="29A12345",
            vehicle_type_id=2,
            card_id=3,
            months=2,
        )
        self.assertEqual(pass_id, 77)
        self.assertEqual(mock_cursor.execute.call_count, 8)

    def test_register_monthly_pass_rejects_card_bound_to_active_pass(self) -> None:
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [
            {"id": 4},                  # monthly tariff
            {"id": 41, "trangthai": 1}, # card is available
            {"id": 1},                  # already bound to active vethang
        ]
        self.mock_db.transaction.return_value.__enter__.return_value = mock_cursor

        with self.assertRaises(ValidationError):
            self.service.register_monthly_pass(
                hoten="Nguyen Van A",
                sdt="0912345678",
                cccd="001095000111",
                customer_type_id=1,
                license_plate="29A12345",
                vehicle_type_id=2,
                card_id=41,
                months=1,
            )

    def test_create_zone_rejects_name_over_5_chars(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.create_zone(1, "KHU_A1")

    def test_reconcile_slot_states_updates_orphaned_slots(self) -> None:
        self.service.reconcile_slot_states()
        query = self.mock_db.execute_non_query.call_args[0][0]
        self.assertIn("UPDATE vitrido", query)
        self.assertIn("SET v.trangthai = 1", query)
        self.assertIn("NOT EXISTS", query)

    def test_get_customers_detail_includes_registered_plates(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_customers_detail()
        query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("bien_so_dang_ky", query)
        self.assertIn("LEFT JOIN phuongtien pt ON pt.id = vt.idpt", query)

    def test_get_walkin_visitors_excludes_monthly_pass_turns(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_walkin_visitors(limit=150)
        query, params = self.mock_db.fetch_all.call_args[0]
        self.assertIn("tt.idvt IS NULL", query)
        self.assertIn("NOT EXISTS", query)
        self.assertIn("FROM vethang vt", query)
        self.assertEqual(params, (150,))

    def test_get_employees_detail_includes_cccd(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_employees_detail()
        query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("nv.cccd", query)

    def test_get_zones_summary_filters_by_lot(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_zones_summary(lot_id=2)
        query, params = self.mock_db.fetch_all.call_args[0]
        self.assertIn("WHERE k.idbdx = %s", query)
        self.assertEqual(params, (2,))

    def test_get_cards_detail_deduplicates_turns_and_passes(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_cards_detail()
        query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("ROW_NUMBER() OVER (PARTITION BY ld.idtx", query)
        self.assertIn("ROW_NUMBER() OVER (PARTITION BY vt.idtx", query)

    def test_get_vehicles_detail_and_revenue_by_lot(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_vehicles_detail()
        v_query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("FROM phuongtien pt", v_query)
        self.assertNotIn("giora IS NULL", v_query)
        self.assertIn("NOT EXISTS", v_query)

        self.service.get_revenue_by_lot()
        l_query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("GROUP BY b.id, b.tenbaido, b.diadiem", l_query)

    def test_get_zones_summary_only_full_group_by_safe(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_zones_summary()
        query = self.mock_db.fetch_all.call_args[0][0]
        self.assertIn("GROUP BY k.id, k.idbdx, k.ten, b.tenbaido, b.diadiem", query)
        self.assertIn("ORDER BY k.idbdx, k.ten", query)
        self.assertNotIn("ORDER BY b.id", query)

    def test_get_cards_detail_uses_unpaid_subquery_not_giora_null(self) -> None:
        self.mock_db.fetch_all.return_value = []
        self.service.get_cards_detail()
        query = self.mock_db.fetch_all.call_args[0][0]
        self.assertNotIn("giora IS NULL", query)
        self.assertIn("NOT EXISTS", query)

    def test_seed_demo_data_removed(self) -> None:
        self.assertFalse(hasattr(self.service, "seed_demo_data"))

    def test_create_card_allocates_manual_id_in_transaction(self) -> None:
        cursor = MagicMock()
        cursor.fetchone.side_effect = [None, {"next_id": 51}]
        self.mock_db.transaction.return_value.__enter__.return_value = cursor

        card_id = self.service.create_card("051")
        self.assertEqual(card_id, 51)
        executed = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("COALESCE(MAX(id), 0) + 1" in sql and "FOR UPDATE" in sql for sql in executed))

    def test_set_slot_maintenance_rejects_occupied_slot(self) -> None:
        cursor = MagicMock()
        cursor.fetchone.return_value = {"id": 1, "trangthai": 0}
        self.mock_db.transaction.return_value.__enter__.return_value = cursor

        with self.assertRaises(ValidationError):
            self.service.set_slot_maintenance(1, True)

    def test_check_out_lost_card_sets_status_2_and_adds_fee(self) -> None:
        self.mock_db.fetch_one.side_effect = [
            {
                "id": 99,
                "giovao": datetime.now() - timedelta(hours=2),
                "idpt": 1,
                "bienso": "29A12345",
                "loaiphuongtien": "Xe máy",
                "loaive": "ngày",
                "dongia": 5000,
            },
            None,
        ]
        cursor = MagicMock()
        cursor.fetchone.side_effect = [{"id": 99, "idvtd": 51, "idtx": 10}, None]
        self.mock_db.transaction.return_value.__enter__.return_value = cursor

        quote = self.service.check_out_vehicle(99, 2001, lost_card=True, lost_card_fee=50000)
        self.assertEqual(quote.amount, 55000)
        self.assertIn("Mất thẻ", quote.ticket_type)
        card_update = cursor.execute.call_args_list[-1]
        self.assertIn("UPDATE thexe SET trangthai = %s", card_update.args[0])
        self.assertEqual(card_update.args[1], (2, 10))

    def test_move_active_turn_slot_swaps_slots_atomically(self) -> None:
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"id": 30, "idvtd": 51},
            None,
            {"id": 55, "trangthai": 1},
        ]
        self.mock_db.transaction.return_value.__enter__.return_value = cursor

        self.service.move_active_turn_slot(30, 55)
        executed = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("UPDATE vitrido SET trangthai = 1" in sql for sql in executed))
        self.assertTrue(any("UPDATE vitrido SET trangthai = 0" in sql for sql in executed))
        self.assertTrue(any("UPDATE luotdo SET idvtd = %s" in sql for sql in executed))

    def test_renew_monthly_pass_extends_end_date(self) -> None:
        cursor = MagicMock()
        future_end = date.today() + timedelta(days=10)
        cursor.fetchone.return_value = {"id": 5, "ngayketthuc": future_end}
        self.mock_db.transaction.return_value.__enter__.return_value = cursor

        res = self.service.renew_monthly_pass(5, 2)
        self.assertEqual(res["new_end_date"], future_end + timedelta(days=60))

    def test_update_payment_status_and_html_builders(self) -> None:
        with self.assertRaises(ValidationError):
            self.service.update_payment_status(1, "Không hợp lệ")

        self.service.update_payment_status(1, "Hoàn tiền")
        self.mock_db.execute_non_query.assert_called_once()

        ticket_html = self.service.build_ticket_html(1, "29A12345", "Xe máy", "Khu A-1", "001", "2026-11-19 08:00:00")
        self.assertIn("PHIẾU GỬI XE", ticket_html)
        self.assertIn("29A12345", ticket_html)

        receipt_html = self.service.build_receipt_html(1, "29A12345", "Vé ngày", "08:00", "10:00", 5000)
        self.assertIn("BIÊN LAI THU PHÍ", receipt_html)
        self.assertIn("5,000 VNĐ", receipt_html)


if __name__ == "__main__":
    unittest.main()
