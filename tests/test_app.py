import os
import sys
import unittest
from datetime import datetime, timedelta
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


if __name__ == "__main__":
    unittest.main()
