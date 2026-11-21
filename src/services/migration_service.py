from __future__ import annotations

import logging
from typing import Any

from services.db_service import DBService

logger = logging.getLogger(__name__)


class MigrationService:
    """Idempotent schema migration runner for production readiness on TiDB/MySQL."""

    def __init__(self, db: DBService) -> None:
        self.db = db

    def _table_exists(self, table_name: str) -> bool:
        row = self.db.fetch_one(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.tables
            WHERE table_schema = DATABASE() AND table_name = %s
            """,
            (table_name,),
        )
        return bool(row and int(row["cnt"]) > 0)

    def _index_exists(self, table_name: str, index_name: str) -> bool:
        row = self.db.fetch_one(
            """
            SELECT COUNT(*) AS cnt
            FROM information_schema.statistics
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND index_name = %s
            """,
            (table_name, index_name),
        )
        return bool(row and int(row["cnt"]) > 0)

    def _column_max_length(self, table_name: str, column_name: str) -> int:
        row = self.db.fetch_one(
            """
            SELECT CHARACTER_MAXIMUM_LENGTH AS max_len
            FROM information_schema.columns
            WHERE table_schema = DATABASE()
              AND table_name = %s
              AND column_name = %s
            """,
            (table_name, column_name),
        )
        if not row or row["max_len"] is None:
            return 0
        return int(row["max_len"])

    def ensure_production_schema(self) -> list[str]:
        """Apply idempotent production migrations and return applied step names."""
        applied: list[str] = []

        # 1. Create production tables if missing
        if not self._table_exists("taikhoan"):
            self.db.execute_non_query(
                """
                CREATE TABLE `taikhoan` (
                  `id` int NOT NULL AUTO_INCREMENT,
                  `idnv` int NOT NULL,
                  `username` varchar(50) NOT NULL,
                  `password_hash` varchar(255) NOT NULL,
                  `role` varchar(20) NOT NULL DEFAULT 'OPERATOR',
                  `is_active` tinyint(1) NOT NULL DEFAULT 1,
                  `last_login_at` datetime DEFAULT NULL,
                  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  UNIQUE KEY `uk_taikhoan_username` (`username`),
                  UNIQUE KEY `uk_taikhoan_idnv` (`idnv`),
                  CONSTRAINT `fk_taikhoan_nhanvien` FOREIGN KEY (`idnv`) REFERENCES `nhanvien` (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
                """
            )
            applied.append("create_table_taikhoan")

        if not self._table_exists("audit_logs"):
            self.db.execute_non_query(
                """
                CREATE TABLE `audit_logs` (
                  `id` bigint NOT NULL AUTO_INCREMENT,
                  `actor_id` int DEFAULT NULL,
                  `actor_username` varchar(50) NOT NULL,
                  `action` varchar(60) NOT NULL,
                  `entity_type` varchar(40) NOT NULL,
                  `entity_id` varchar(64) DEFAULT NULL,
                  `details_json` text,
                  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  PRIMARY KEY (`id`),
                  KEY `idx_audit_created` (`created_at`),
                  KEY `idx_audit_entity` (`entity_type`, `entity_id`),
                  KEY `idx_audit_actor` (`actor_id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
                """
            )
            applied.append("create_table_audit_logs")

        if not self._table_exists("ca_lam_viec"):
            self.db.execute_non_query(
                """
                CREATE TABLE `ca_lam_viec` (
                  `id` int NOT NULL AUTO_INCREMENT,
                  `idnv` int NOT NULL,
                  `idbdx` int DEFAULT NULL,
                  `started_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
                  `ended_at` datetime DEFAULT NULL,
                  `opening_cash` int NOT NULL DEFAULT 0,
                  `expected_cash` int NOT NULL DEFAULT 0,
                  `actual_cash` int DEFAULT NULL,
                  `transfer_total` int NOT NULL DEFAULT 0,
                  `note` varchar(255) DEFAULT NULL,
                  `status` varchar(20) NOT NULL DEFAULT 'OPEN',
                  PRIMARY KEY (`id`),
                  KEY `idx_shift_status` (`status`, `started_at`),
                  CONSTRAINT `fk_shift_nhanvien` FOREIGN KEY (`idnv`) REFERENCES `nhanvien` (`id`),
                  CONSTRAINT `fk_shift_baidoxe` FOREIGN KEY (`idbdx`) REFERENCES `baidoxe` (`id`)
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_bin
                """
            )
            applied.append("create_table_ca_lam_viec")

        # 2. Widen narrow varchar columns safely
        widen_specs: list[tuple[str, str, int, str]] = [
            ("phuongtien", "bienso", 15, "varchar(15) NOT NULL"),
            ("baidoxe", "tenbaido", 100, "varchar(100) NOT NULL"),
            ("baidoxe", "diadiem", 255, "varchar(255) NOT NULL"),
            ("nhanvien", "hoten", 60, "varchar(60) DEFAULT NULL"),
            ("nhanvien", "chucvu", 30, "varchar(30) NOT NULL"),
            ("nhanvien", "sdt", 15, "varchar(15) NOT NULL"),
            ("nhanvien", "email", 100, "varchar(100) DEFAULT NULL"),
            ("thanhtoan", "trangthai", 30, "varchar(30) NOT NULL"),
            ("thanhtoan", "loaithanhtoan", 30, "varchar(30) NOT NULL"),
        ]
        for table, col, min_len, col_def in widen_specs:
            if self._column_max_length(table, col) < min_len:
                self.db.execute_non_query(f"ALTER TABLE `{table}` MODIFY COLUMN `{col}` {col_def}")
                applied.append(f"widen_{table}_{col}")

        # 3. Add performance & integrity indexes
        if not self._index_exists("thanhtoan", "uk_thanhtoan_idld"):
            dup = self.db.fetch_one(
                """
                SELECT COUNT(*) AS cnt FROM (
                    SELECT idld FROM thanhtoan
                    WHERE idld IS NOT NULL
                    GROUP BY idld HAVING COUNT(*) > 1
                ) t
                """
            )
            if dup and int(dup["cnt"]) == 0:
                self.db.execute_non_query(
                    "ALTER TABLE `thanhtoan` ADD UNIQUE KEY `uk_thanhtoan_idld` (`idld`)"
                )
                applied.append("add_uk_thanhtoan_idld")

        index_specs: list[tuple[str, str, str]] = [
            ("luotdo", "idx_luotdo_time", "(`giovao`, `giora`)"),
            ("thanhtoan", "idx_thanhtoan_time_status", "(`giothanhtoan`, `trangthai`)"),
            ("vethang", "idx_vethang_dates", "(`ngaybatdau`, `ngayketthuc`)"),
        ]
        for table, idx_name, cols in index_specs:
            if not self._index_exists(table, idx_name):
                self.db.execute_non_query(f"ALTER TABLE `{table}` ADD INDEX `{idx_name}` {cols}")
                applied.append(f"add_{idx_name}")

        if applied:
            logger.info("Applied production migrations: %s", ", ".join(applied))
        return applied
