from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from api.deps import get_auth_service, get_db, get_parking_service
from api.main import app
from services.auth_service import AuthService, AuthUser, hash_password, verify_password
from services.db_service import DBService
from services.parking_service import ParkingService


class TestAuthAndProductionServices(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_db = MagicMock(spec=DBService)
        self.mock_db.config = MagicMock(host="localhost", database="dbptit", user="root")
        self.auth = AuthService(self.mock_db, secret_key="test-secret-key")
        self.parking = ParkingService(self.mock_db)

    def test_password_hash_and_verify_roundtrip(self) -> None:
        hashed = hash_password("Secret@123")
        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password("Secret@123", hashed))
        self.assertFalse(verify_password("WrongPass", hashed))

    def test_jwt_token_roundtrip(self) -> None:
        user = AuthUser(
            account_id=1,
            employee_id=3,
            username="admin",
            full_name="Lê Minh Cường",
            role="ADMIN",
            lot_id=1,
        )
        token = self.auth.create_token(user, ttl_seconds=600)
        decoded = self.auth.verify_token(token)
        self.assertEqual(decoded.username, "admin")
        self.assertEqual(decoded.role, "ADMIN")
        self.assertEqual(decoded.employee_id, 3)

    def test_register_monthly_pass_records_payment_when_employee_present(self) -> None:
        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"id": 4, "dongia": 100000},  # monthly tariff with dongia
            {"id": 3, "trangthai": 1},    # card available
            None,                         # no active pass on card
            {"id": 10},                   # existing customer
            {"id": 20},                   # existing vehicle
        ]
        cursor.lastrowid = 88
        self.mock_db.transaction.return_value.__enter__.return_value = cursor

        pass_id = self.parking.register_monthly_pass(
            hoten="Nguyen Van A",
            sdt="0912345678",
            cccd="001095000111",
            customer_type_id=1,
            license_plate="29A12345",
            vehicle_type_id=2,
            card_id=3,
            months=3,
            employee_id=3,
            payment_method="Chuyển khoản",
        )
        self.assertEqual(pass_id, 88)
        executed_sql = [call.args[0] for call in cursor.execute.call_args_list]
        self.assertTrue(any("INSERT INTO thanhtoan" in sql for sql in executed_sql))

    def test_open_and_close_shift(self) -> None:
        self.mock_db.fetch_one.return_value = None
        self.mock_db.execute_non_query.return_value = 55
        shift_id = self.parking.open_shift(employee_id=3, lot_id=1, opening_cash=500000)
        self.assertEqual(shift_id, 55)

        cursor = MagicMock()
        cursor.fetchone.side_effect = [
            {"id": 55, "idnv": 3, "opening_cash": 500000, "started_at": "2026-11-21 08:00:00", "status": "OPEN"},
            {"cash_total": 120000, "transfer_total": 80000},
        ]
        self.mock_db.transaction.return_value.__enter__.return_value = cursor
        res = self.parking.close_shift(55, 3, actual_cash=620000, note="Đủ tiền")
        self.assertEqual(res["expected_cash"], 620000)
        self.assertEqual(res["diff"], 0)
        self.assertEqual(res["transfer_total"], 80000)


class TestFastAPIRoutes(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_db = MagicMock(spec=DBService)
        self.mock_db.config = MagicMock(host="localhost", database="dbptit", user="root")
        self.mock_db.test_connection.return_value = (True, "OK")
        self.auth = AuthService(self.mock_db, secret_key="api-test-secret")
        self.mock_parking = MagicMock(spec=ParkingService)

        app.dependency_overrides[get_db] = lambda: self.mock_db
        app.dependency_overrides[get_auth_service] = lambda: self.auth
        app.dependency_overrides[get_parking_service] = lambda: self.mock_parking
        self.client = TestClient(app)

    def tearDown(self) -> None:
        app.dependency_overrides.clear()

    def test_protected_route_requires_auth(self) -> None:
        res = self.client.get("/api/overview")
        self.assertEqual(res.status_code, 401)

    def test_rbac_blocks_operator_from_admin_accounts(self) -> None:
        operator = AuthUser(2, 1001, "baove", "Nguyễn Văn An", "OPERATOR", 1)
        token = self.auth.create_token(operator)
        res = self.client.get(
            "/api/accounts",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 403)

    def test_admin_can_access_accounts_and_analytics(self) -> None:
        admin = AuthUser(1, 3, "admin", "Lê Minh Cường", "ADMIN", 1)
        token = self.auth.create_token(admin)
        self.mock_db.fetch_all.return_value = []
        self.mock_parking.get_daily_revenue.return_value = []
        self.mock_parking.get_revenue_by_vehicle_type.return_value = []
        self.mock_parking.get_revenue_by_lot.return_value = []
        self.mock_parking.get_monthly_pass_revenue_summary.return_value = {}

        res = self.client.get(
            "/api/analytics/summary?days=30",
            headers={"Authorization": f"Bearer {token}"},
        )
        self.assertEqual(res.status_code, 200)


if __name__ == "__main__":
    unittest.main()
