from __future__ import annotations

import hashlib
import logging
import os
import threading
import time
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, Iterator, Optional, Sequence, TypeVar

import mysql.connector
from mysql.connector import Error, pooling
from mysql.connector.connection import MySQLConnection

logger = logging.getLogger(__name__)
_T = TypeVar("_T")
_TRANSIENT_ERRNOS = {1205, 1213, 2006, 2013}


@dataclass(frozen=True)
class DBConfig:
    """Immutable database connection configuration."""

    host: str
    database: str
    user: str
    password: str
    port: int = 4000
    ssl_ca: Optional[str] = None


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
        pool_size: int = 5,
        ssl_ca: Optional[str] = None,
    ) -> None:
        self.config = DBConfig(
            host=host,
            database=database,
            user=user,
            password=password,
            port=port,
            ssl_ca=ssl_ca,
        )
        self._pool_size = pool_size
        self._pool: Optional[pooling.MySQLConnectionPool] = None
        self._pool_lock = threading.Lock()

    @classmethod
    def from_config(cls, config: DBConfig) -> DBService:
        """Instantiate DBService from a DBConfig instance."""
        return cls(
            host=config.host,
            database=config.database,
            user=config.user,
            password=config.password,
            port=config.port,
            ssl_ca=config.ssl_ca,
        )

    @classmethod
    def from_env(cls) -> Optional[DBService]:
        """Load DBService from environment variables if present."""
        host = os.getenv("TIDB_HOST")
        database = os.getenv("TIDB_DATABASE")
        user = os.getenv("TIDB_USER")
        password = os.getenv("TIDB_PASSWORD")
        port_raw = os.getenv("TIDB_PORT", "4000")
        pool_raw = os.getenv("TIDB_POOL_SIZE", "8")
        ssl_ca = os.getenv("TIDB_SSL_CA")
        if host and database and user and password:
            return cls(
                host=host,
                database=database,
                user=user,
                password=password,
                port=int(port_raw),
                pool_size=max(2, int(pool_raw)),
                ssl_ca=ssl_ca or None,
            )
        return None

    def _get_pool(self) -> pooling.MySQLConnectionPool:
        """Lazily initialize and return the thread-safe MySQL connection pool."""
        if self._pool is None:
            with self._pool_lock:
                if self._pool is None:
                    raw_key = f"{self.config.host}:{self.config.port}/{self.config.database}/{self.config.user}"
                    pool_name = "ptit_" + hashlib.sha1(raw_key.encode("utf-8")).hexdigest()[:12]
                    pool_kwargs: dict[str, Any] = {
                        "pool_name": pool_name,
                        "pool_size": self._pool_size,
                        "pool_reset_session": True,
                        "host": self.config.host,
                        "port": self.config.port,
                        "database": self.config.database,
                        "user": self.config.user,
                        "password": self.config.password,
                        "connection_timeout": 10,
                    }
                    if self.config.ssl_ca:
                        pool_kwargs["ssl_ca"] = self.config.ssl_ca
                        pool_kwargs["ssl_verify_cert"] = True
                    self._pool = pooling.MySQLConnectionPool(**pool_kwargs)
        return self._pool

    def _run_with_retry(self, fn: Callable[[], _T], max_attempts: int = 3) -> _T:
        """Retry transient MySQL/TiDB errors with exponential backoff."""
        delay = 0.15
        for attempt in range(1, max_attempts + 1):
            try:
                return fn()
            except Error as exc:
                if getattr(exc, "errno", None) in _TRANSIENT_ERRNOS and attempt < max_attempts:
                    logger.warning(
                        "Transient DB error (errno=%s, attempt=%s/%s): %s",
                        getattr(exc, "errno", None),
                        attempt,
                        max_attempts,
                        exc,
                    )
                    time.sleep(delay)
                    delay *= 2
                    continue
                raise
        raise DatabaseError("Lỗi kết nối cơ sở dữ liệu sau nhiều lần thử lại")

    def get_connection(self) -> MySQLConnection:
        """Borrow a pooled database connection (reconnecting if stale)."""
        try:
            conn = self._get_pool().get_connection()
            if not conn.is_connected():
                conn.ping(reconnect=True, attempts=1, delay=0)
            return conn  # type: ignore[return-value]
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
        def _exec() -> list[dict[str, Any]]:
            conn: Optional[MySQLConnection] = None
            cursor = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute(query, params)
                rows = cursor.fetchall()
                return list(rows) if rows else []
            finally:
                if cursor is not None:
                    cursor.close()
                if conn is not None and conn.is_connected():
                    conn.close()

        try:
            return self._run_with_retry(_exec)
        except Error as exc:
            raise DatabaseError(f"Lỗi truy vấn dữ liệu: {exc}") from exc

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
        def _exec() -> int:
            conn: Optional[MySQLConnection] = None
            cursor = None
            try:
                conn = self.get_connection()
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return int(cursor.lastrowid) if cursor.lastrowid else int(cursor.rowcount)
            except Error:
                if conn is not None:
                    conn.rollback()
                raise
            finally:
                if cursor is not None:
                    cursor.close()
                if conn is not None and conn.is_connected():
                    conn.close()

        try:
            return self._run_with_retry(_exec)
        except Error as exc:
            raise DatabaseError(f"Lỗi cập nhật dữ liệu: {exc}") from exc

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

    @contextmanager
    def transaction(self) -> Iterator[Any]:
        """Provide a transactional dictionary cursor with automatic commit/rollback."""
        conn: Optional[MySQLConnection] = None
        cursor = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            yield cursor
            conn.commit()
        except Error as exc:
            if conn is not None:
                conn.rollback()
            raise DatabaseError(f"Lỗi giao dịch cơ sở dữ liệu: {exc}") from exc
        except Exception:
            if conn is not None:
                conn.rollback()
            raise
        finally:
            if cursor is not None:
                cursor.close()
            if conn is not None and conn.is_connected():
                conn.close()
