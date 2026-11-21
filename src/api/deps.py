from __future__ import annotations

import os
import tomllib
from functools import lru_cache
from pathlib import Path
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from services.auth_service import AuthenticationError, AuthService, AuthUser
from services.db_service import DatabaseError, DBService
from services.parking_service import ParkingService

_bearer_scheme = HTTPBearer(auto_error=False)


def _load_db_service() -> DBService:
    env_db = DBService.from_env()
    if env_db is not None:
        return env_db

    secrets_path = Path(__file__).resolve().parents[2] / ".streamlit" / "secrets.toml"
    if secrets_path.exists():
        with secrets_path.open("rb") as f:
            data = tomllib.load(f)
        tidb = data.get("tidb", {})
        if tidb.get("host") and tidb.get("database") and tidb.get("user") and tidb.get("password"):
            return DBService(
                host=str(tidb["host"]),
                port=int(tidb.get("port", 4000)),
                database=str(tidb["database"]),
                user=str(tidb["user"]),
                password=str(tidb["password"]),
                pool_size=int(os.getenv("TIDB_POOL_SIZE", "8")),
                ssl_ca=tidb.get("ssl_ca"),
            )
    raise DatabaseError("Thiếu cấu hình kết nối DB (TIDB_* env vars hoặc .streamlit/secrets.toml).")


@lru_cache(maxsize=1)
def get_db() -> DBService:
    return _load_db_service()


def get_parking_service(db: DBService = Depends(get_db)) -> ParkingService:
    return ParkingService(db)


def get_auth_service(db: DBService = Depends(get_db)) -> AuthService:
    return AuthService(db)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    auth: AuthService = Depends(get_auth_service),
) -> AuthUser:
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Vui lòng đăng nhập để tiếp tục.",
        )
    try:
        return auth.verify_token(credentials.credentials)
    except AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(exc),
        ) from exc


def require_roles(*roles: str) -> Callable[[AuthUser], AuthUser]:
    allowed = {r.upper() for r in roles}

    def _checker(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if user.role.upper() not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Bạn không có quyền thực hiện thao tác này.",
            )
        return user

    return _checker
