from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional, Sequence

import mysql.connector
from mysql.connector import Error
from mysql.connector.connection import MySQLConnection


@dataclass(frozen=True)
class DBConfig:
    """Immutable database connection configuration."""

    host: str
    database: str
    user: str
    password: str
    port: int = 4000


class DatabaseError(RuntimeError):
    """Raised when a database connection or query fails."""


class DBService:
    """Infrastructure service managing MySQL/TiDB connections and queries."""

    def __init__(
        self,
        host: str,
        database: str,
        user: str,
        password: str,
        port: int = 4000,
    ) -> None:
        self.config = DBConfig(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
        )

    @classmethod
    def from_config(cls, config: DBConfig) -> DBService:
        """Instantiate DBService from a DBConfig instance."""
        return cls(
            host=config.host,
            database=config.database,
            user=config.user,
            password=config.password,
            port=config.port,
        )

    @classmethod
    def from_env(cls) -> Optional[DBService]:
        """Load DBService from environment variables if present."""
        host = os.getenv("TIDB_HOST")
        database = os.getenv("TIDB_DATABASE")
        user = os.getenv("TIDB_USER")
        password = os.getenv("TIDB_PASSWORD")
        port_raw = os.getenv("TIDB_PORT", "4000")
        if host and database and user and password:
            return cls(
                host=host,
                database=database,
                user=user,
                password=password,
                port=int(port_raw),
            )
        return None

    def get_connection(self) -> MySQLConnection:
        """Create and return a new database connection."""
        try:
            return mysql.connector.connect(
                host=self.config.host,
                port=self.config.port,
                database=self.config.database,
                user=self.config.user,
                password=self.config.password,
                connection_timeout=10,
            )
        except Error as exc:
            raise DatabaseError(f"Không thể kết nối tới cơ sở dữ liệu: {exc}") from exc

    def test_connection(self) -> tuple[bool, str]:
        """Verify database connectivity and return (ok, message)."""
        conn: Optional[MySQLConnection] = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            return True, "Kết nối TiDB Cloud thành công"
        except Exception as exc:
            return False, str(exc)
        finally:
            if conn is not None and conn.is_connected():
                conn.close()

    def fetch_all(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> list[dict[str, Any]]:
        """Execute a SELECT query and return all rows as dictionaries."""
        conn: Optional[MySQLConnection] = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            rows = cursor.fetchall()
            return list(rows) if rows else []
        except Error as exc:
            raise DatabaseError(f"Lỗi truy vấn dữ liệu: {exc}") from exc
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()

    def fetch_one(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Execute a SELECT query and return a single row or None."""
        rows = self.fetch_all(query, params)
        return rows[0] if rows else None

    def execute_query(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> list[dict[str, Any]]:
        """Backward-compatible alias for fetch_all."""
        return self.fetch_all(query, params)

    def execute_non_query(
        self,
        query: str,
        params: Optional[Sequence[Any]] = None,
    ) -> int:
        """Execute an INSERT/UPDATE/DELETE query and return lastrowid or rowcount."""
        conn: Optional[MySQLConnection] = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return int(cursor.lastrowid) if cursor.lastrowid else int(cursor.rowcount)
        except Error as exc:
            if conn is not None:
                conn.rollback()
            raise DatabaseError(f"Lỗi cập nhật dữ liệu: {exc}") from exc
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()

    def execute_transaction(
        self,
        operations: Sequence[tuple[str, Optional[Sequence[Any]]]],
    ) -> None:
        """Execute multiple SQL statements atomically in a single transaction."""
        conn: Optional[MySQLConnection] = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            for query, params in operations:
                cursor.execute(query, params)
            conn.commit()
        except Error as exc:
            if conn is not None:
                conn.rollback()
            raise DatabaseError(f"Lỗi giao dịch cơ sở dữ liệu: {exc}") from exc
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()
