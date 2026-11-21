from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any, Optional

from services.db_service import DBService
from services.parking_service import ValidationError

VALID_ROLES = ("ADMIN", "ACCOUNTANT", "OPERATOR")


class AuthenticationError(ValueError):
    """Raised when credentials or session tokens are invalid."""


@dataclass(frozen=True)
class AuthUser:
    """Authenticated operator or administrator identity."""

    account_id: int
    employee_id: int
    username: str
    full_name: str
    role: str
    lot_id: Optional[int]


def _b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("ascii")


def _b64url_decode(data: str) -> bytes:
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def hash_password(password: str) -> str:
    """Hash a plaintext password using PBKDF2-HMAC-SHA256 with random salt."""
    if len(password) < 6:
        raise ValidationError("Mật khẩu phải có ít nhất 6 ký tự.")
    salt = secrets.token_bytes(16)
    iterations = 120_000
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return f"pbkdf2_sha256${iterations}${_b64url_encode(salt)}${_b64url_encode(dk)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash."""
    try:
        scheme, iter_raw, salt_b64, dk_b64 = stored_hash.split("$", 3)
        if scheme != "pbkdf2_sha256":
            return False
        iterations = int(iter_raw)
        salt = _b64url_decode(salt_b64)
        expected = _b64url_decode(dk_b64)
    except Exception:
        return False
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)
    return hmac.compare_digest(candidate, expected)


class AuthService:
    """Authentication, RBAC, and operator account management."""

    def __init__(self, db: DBService, secret_key: Optional[str] = None) -> None:
        self.db = db
        self._secret_key = (
            secret_key
            or os.getenv("AUTH_SECRET_KEY")
            or hashlib.sha256(
                f"{db.config.host}:{db.config.database}:{db.config.user}:smart-parking".encode("utf-8")
            ).hexdigest()
        ).encode("utf-8")

    def create_token(self, user: AuthUser, ttl_seconds: int = 12 * 3600) -> str:
        """Issue an HS256-signed bearer token for an authenticated user."""
        header = _b64url_encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode("utf-8"))
        now = int(time.time())
        payload = _b64url_encode(
            json.dumps(
                {
                    "sub": user.account_id,
                    "emp_id": user.employee_id,
                    "username": user.username,
                    "full_name": user.full_name,
                    "role": user.role,
                    "lot_id": user.lot_id,
                    "iat": now,
                    "exp": now + ttl_seconds,
                }
            ).encode("utf-8")
        )
        signing_input = f"{header}.{payload}".encode("ascii")
        sig = _b64url_encode(hmac.new(self._secret_key, signing_input, hashlib.sha256).digest())
        return f"{header}.{payload}.{sig}"

    def verify_token(self, token: str) -> AuthUser:
        """Validate an HS256 token and return the embedded AuthUser."""
        try:
            header_b64, payload_b64, sig_b64 = token.split(".", 2)
        except ValueError as exc:
            raise AuthenticationError("Token không hợp lệ.") from exc

        signing_input = f"{header_b64}.{payload_b64}".encode("ascii")
        expected_sig = _b64url_encode(
            hmac.new(self._secret_key, signing_input, hashlib.sha256).digest()
        )
        if not hmac.compare_digest(sig_b64, expected_sig):
            raise AuthenticationError("Chữ ký token không hợp lệ.")

        try:
            claims = json.loads(_b64url_decode(payload_b64).decode("utf-8"))
        except Exception as exc:
            raise AuthenticationError("Không thể giải mã phiên đăng nhập.") from exc

        if int(claims.get("exp", 0)) < int(time.time()):
            raise AuthenticationError("Phiên đăng nhập đã hết hạn. Vui lòng đăng nhập lại.")

        return AuthUser(
            account_id=int(claims["sub"]),
            employee_id=int(claims["emp_id"]),
            username=str(claims["username"]),
            full_name=str(claims["full_name"]),
            role=str(claims["role"]),
            lot_id=int(claims["lot_id"]) if claims.get("lot_id") is not None else None,
        )

    def authenticate(self, username: str, password: str) -> AuthUser:
        """Verify username and password and update last_login_at."""
        clean_user = (username or "").strip().lower()
        if not clean_user or not password:
            raise AuthenticationError("Vui lòng nhập tên đăng nhập và mật khẩu.")

        row = self.db.fetch_one(
            """
            SELECT tk.id, tk.idnv, tk.username, tk.password_hash, tk.role, tk.is_active,
                   nv.hoten, nv.idbdx
            FROM taikhoan tk
            JOIN nhanvien nv ON nv.id = tk.idnv
            WHERE tk.username = %s
            """,
            (clean_user,),
        )
        if not row or not verify_password(password, str(row["password_hash"])):
            raise AuthenticationError("Tên đăng nhập hoặc mật khẩu không đúng.")
        if not int(row["is_active"]):
            raise AuthenticationError("Tài khoản đã bị khóa. Liên hệ quản trị viên.")

        self.db.execute_non_query(
            "UPDATE taikhoan SET last_login_at = NOW() WHERE id = %s",
            (int(row["id"]),),
        )
        return AuthUser(
            account_id=int(row["id"]),
            employee_id=int(row["idnv"]),
            username=str(row["username"]),
            full_name=str(row["hoten"] or row["username"]),
            role=str(row["role"]),
            lot_id=int(row["idbdx"]) if row["idbdx"] is not None else None,
        )

    def ensure_default_accounts(self) -> int:
        """Seed initial accounts from existing nhanvien rows when taikhoan is empty."""
        count_row = self.db.fetch_one("SELECT COUNT(*) AS cnt FROM taikhoan")
        if count_row and int(count_row["cnt"]) > 0:
            return 0

        employees = self.db.fetch_all(
            "SELECT id, hoten, chucvu FROM nhanvien ORDER BY id"
        )
        if not employees:
            return 0

        role_by_position = {
            "quản lý": "ADMIN",
            "thu ngân": "ACCOUNTANT",
            "bảo vệ": "OPERATOR",
        }
        default_pw_hash = hash_password("123456")
        created = 0
        used_usernames: set[str] = set()

        for emp in employees:
            pos = str(emp.get("chucvu") or "").strip().lower()
            role = role_by_position.get(pos, "OPERATOR")
            if role == "ADMIN" and "admin" not in used_usernames:
                uname = "admin"
            elif role == "ACCOUNTANT" and "thungan" not in used_usernames:
                uname = "thungan"
            elif role == "OPERATOR" and "baove" not in used_usernames:
                uname = "baove"
            else:
                uname = f"nv{int(emp['id'])}"
            used_usernames.add(uname)

            self.db.execute_non_query(
                """
                INSERT INTO taikhoan (idnv, username, password_hash, role, is_active)
                VALUES (%s, %s, %s, %s, 1)
                """,
                (int(emp["id"]), uname, default_pw_hash, role),
            )
            created += 1
        return created

    def list_accounts(self) -> list[dict[str, Any]]:
        """List all operator accounts joined with employee and parking lot info."""
        return self.db.fetch_all(
            """
            SELECT tk.id, tk.idnv, tk.username, tk.role, tk.is_active,
                   tk.last_login_at, tk.created_at,
                   nv.hoten AS ten_nhanvien, nv.chucvu, nv.sdt, nv.email,
                   bdx.tenbaido
            FROM taikhoan tk
            JOIN nhanvien nv ON nv.id = tk.idnv
            LEFT JOIN baidoxe bdx ON bdx.id = nv.idbdx
            ORDER BY tk.id
            """
        )

    def create_account(
        self, employee_id: int, username: str, password: str, role: str
    ) -> int:
        """Create a login account linked to an employee."""
        clean_user = (username or "").strip().lower()
        if len(clean_user) < 3 or len(clean_user) > 50 or not clean_user.replace("_", "").replace(".", "").isalnum():
            raise ValidationError("Tên đăng nhập phải dài 3-50 ký tự (chữ, số, '.', '_').")
        clean_role = role.strip().upper()
        if clean_role not in VALID_ROLES:
            raise ValidationError("Vai trò không hợp lệ.")

        pw_hash = hash_password(password)
        existing_emp = self.db.fetch_one("SELECT id FROM nhanvien WHERE id = %s", (employee_id,))
        if not existing_emp:
            raise ValidationError("Không tìm thấy nhân viên.")
        dup_user = self.db.fetch_one("SELECT id FROM taikhoan WHERE username = %s", (clean_user,))
        if dup_user:
            raise ValidationError("Tên đăng nhập đã tồn tại.")
        dup_emp = self.db.fetch_one("SELECT id FROM taikhoan WHERE idnv = %s", (employee_id,))
        if dup_emp:
            raise ValidationError("Nhân viên này đã có tài khoản.")

        return self.db.execute_non_query(
            """
            INSERT INTO taikhoan (idnv, username, password_hash, role, is_active)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (employee_id, clean_user, pw_hash, clean_role),
        )

    def update_account(
        self,
        account_id: int,
        role: Optional[str] = None,
        is_active: Optional[bool] = None,
        new_password: Optional[str] = None,
    ) -> None:
        """Update role, active status, or password of an account."""
        sets: list[str] = []
        params: list[Any] = []
        if role is not None:
            clean_role = role.strip().upper()
            if clean_role not in VALID_ROLES:
                raise ValidationError("Vai trò không hợp lệ.")
            sets.append("role = %s")
            params.append(clean_role)
        if is_active is not None:
            sets.append("is_active = %s")
            params.append(1 if is_active else 0)
        if new_password:
            sets.append("password_hash = %s")
            params.append(hash_password(new_password))

        if not sets:
            return
        params.append(account_id)
        affected = self.db.execute_non_query(
            f"UPDATE taikhoan SET {', '.join(sets)} WHERE id = %s",
            tuple(params),
        )
        if affected == 0:
            raise ValidationError("Không tìm thấy tài khoản.")

    def change_own_password(
        self, account_id: int, old_password: str, new_password: str
    ) -> None:
        """Allow an authenticated user to change their own password."""
        row = self.db.fetch_one(
            "SELECT password_hash FROM taikhoan WHERE id = %s",
            (account_id,),
        )
        if not row or not verify_password(old_password, str(row["password_hash"])):
            raise ValidationError("Mật khẩu hiện tại không đúng.")
        new_hash = hash_password(new_password)
        self.db.execute_non_query(
            "UPDATE taikhoan SET password_hash = %s WHERE id = %s",
            (new_hash, account_id),
        )
