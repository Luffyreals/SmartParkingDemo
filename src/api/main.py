from __future__ import annotations

import logging
import sys
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import date, datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import Depends, FastAPI, Query, Request, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

_SRC_DIR = str(Path(__file__).resolve().parents[1])
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from api.deps import (
    get_auth_service,
    get_current_user,
    get_db,
    get_parking_service,
    require_roles,
)
from api.schemas import (
    AccountCreateRequest,
    AccountUpdateRequest,
    AddSlotsRequest,
    CardCreateRequest,
    CardStatusRequest,
    ChangePasswordRequest,
    CheckInRequest,
    CheckOutRequest,
    CustomerUpdateRequest,
    EmployeeRequest,
    LoginRequest,
    LotRequest,
    MoveSlotRequest,
    PassAssetsUpdateRequest,
    PassRegisterRequest,
    PassRenewRequest,
    PaymentStatusRequest,
    ShiftCloseRequest,
    ShiftOpenRequest,
    SlotMaintenanceRequest,
    TariffCreateRequest,
    TariffUpdateRequest,
    VehicleUpdateRequest,
    ZoneRequest,
)
from services.auth_service import AuthenticationError, AuthService, AuthUser
from services.db_service import DatabaseError
from services.migration_service import MigrationService
from services.parking_service import ParkingService, ValidationError

logger = logging.getLogger(__name__)


class LiveConnectionManager:
    """Manages active WebSocket clients for real-time parking lot updates."""

    def __init__(self) -> None:
        self._connections: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.append(ws)

    def disconnect(self, ws: WebSocket) -> None:
        if ws in self._connections:
            self._connections.remove(ws)

    async def broadcast(self, event_type: str, payload: Optional[dict[str, Any]] = None) -> None:
        message = jsonable_encoder(
            {
                "event": event_type,
                "payload": payload or {},
                "timestamp": datetime.now().isoformat(timespec="seconds"),
            }
        )
        dead: list[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_json(message)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


ws_manager = LiveConnectionManager()


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        db = get_db()
        MigrationService(db).ensure_production_schema()
        AuthService(db).ensure_default_accounts()
    except Exception as exc:
        logger.warning("Startup migration/seed skipped or failed: %s", exc)
    yield


app = FastAPI(
    title="Smart Parking System API",
    version="2.0.0",
    description="Production REST & WebSocket API for Smart Parking Management",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(ValidationError)
async def validation_error_handler(_req: Request, exc: ValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"detail": str(exc)})


@app.exception_handler(AuthenticationError)
async def auth_error_handler(_req: Request, exc: AuthenticationError) -> JSONResponse:
    return JSONResponse(status_code=401, content={"detail": str(exc)})


@app.exception_handler(DatabaseError)
async def db_error_handler(_req: Request, exc: DatabaseError) -> JSONResponse:
    return JSONResponse(status_code=503, content={"detail": str(exc)})


# ------------------------------------------------------------------
# Health & WebSocket
# ------------------------------------------------------------------


@app.get("/api/health")
def health_check() -> dict[str, Any]:
    db = get_db()
    ok, msg = db.test_connection()
    return {"ok": ok, "message": msg}


@app.websocket("/ws/live")
async def websocket_live(ws: WebSocket) -> None:
    await ws_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(ws)


# ------------------------------------------------------------------
# Auth & Account Management
# ------------------------------------------------------------------


@app.post("/api/auth/login")
def login(body: LoginRequest, auth: AuthService = Depends(get_auth_service)) -> dict[str, Any]:
    user = auth.authenticate(body.username, body.password)
    token = auth.create_token(user)
    return {"access_token": token, "token_type": "bearer", "user": asdict(user)}


@app.get("/api/auth/me")
def me(user: AuthUser = Depends(get_current_user)) -> dict[str, Any]:
    return asdict(user)


@app.post("/api/auth/change-password")
def change_password(
    body: ChangePasswordRequest,
    user: AuthUser = Depends(get_current_user),
    auth: AuthService = Depends(get_auth_service),
) -> dict[str, str]:
    auth.change_own_password(user.account_id, body.old_password, body.new_password)
    return {"message": "Đổi mật khẩu thành công."}


@app.get("/api/accounts")
def list_accounts(
    _user: AuthUser = Depends(require_roles("ADMIN")),
    auth: AuthService = Depends(get_auth_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(auth.list_accounts())


@app.post("/api/accounts")
def create_account(
    body: AccountCreateRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    auth: AuthService = Depends(get_auth_service),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    acc_id = auth.create_account(body.employee_id, body.username, body.password, body.role)
    service.record_audit_log(
        user.account_id,
        user.username,
        "CREATE_ACCOUNT",
        "taikhoan",
        acc_id,
        {"username": body.username, "role": body.role, "employee_id": body.employee_id},
    )
    return {"id": acc_id}


@app.patch("/api/accounts/{account_id}")
def update_account(
    account_id: int,
    body: AccountUpdateRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    auth: AuthService = Depends(get_auth_service),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    auth.update_account(
        account_id,
        role=body.role,
        is_active=body.is_active,
        new_password=body.new_password,
    )
    service.record_audit_log(
        user.account_id,
        user.username,
        "UPDATE_ACCOUNT",
        "taikhoan",
        account_id,
        {"role": body.role, "is_active": body.is_active, "password_reset": bool(body.new_password)},
    )
    return {"message": "Đã cập nhật tài khoản."}


# ------------------------------------------------------------------
# Overview, Alerts & Infrastructure (Lots / Zones / Slots)
# ------------------------------------------------------------------


@app.get("/api/overview")
def get_overview(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    metrics = service.get_overview_metrics()
    return jsonable_encoder(
        {
            "metrics": asdict(metrics),
            "lots": service.get_parking_lots(),
            "zones": service.get_zones_summary(),
        }
    )


@app.get("/api/alerts")
def get_alerts(
    overdue_hours: int = Query(default=24, ge=1, le=720),
    pass_expiring_days: int = Query(default=7, ge=1, le=60),
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    return jsonable_encoder(
        service.get_operational_alerts(
            overdue_hours=overdue_hours,
            pass_expiring_days=pass_expiring_days,
        )
    )


@app.get("/api/lots")
def list_lots(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_parking_lots())


@app.post("/api/lots")
async def create_lot(
    body: LotRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    lot_id = service.create_parking_lot(body.name, body.location)
    service.record_audit_log(user.account_id, user.username, "CREATE_LOT", "baidoxe", lot_id, body.model_dump())
    await ws_manager.broadcast("infrastructure_updated")
    return {"id": lot_id}


@app.put("/api/lots/{lot_id}")
async def update_lot(
    lot_id: int,
    body: LotRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_parking_lot(lot_id, body.name, body.location)
    service.record_audit_log(user.account_id, user.username, "UPDATE_LOT", "baidoxe", lot_id, body.model_dump())
    await ws_manager.broadcast("infrastructure_updated")
    return {"message": "Đã cập nhật bãi đỗ."}


@app.delete("/api/lots/{lot_id}")
async def delete_lot(
    lot_id: int,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_parking_lot(lot_id)
    service.record_audit_log(user.account_id, user.username, "DELETE_LOT", "baidoxe", lot_id)
    await ws_manager.broadcast("infrastructure_updated")
    return {"message": "Đã xóa bãi đỗ."}


@app.get("/api/zones")
def list_zones(
    lot_id: Optional[int] = None,
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_zones_summary(lot_id=lot_id))


@app.post("/api/zones")
async def create_zone(
    body: ZoneRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    zone_id = service.create_zone(body.lot_id, body.name)
    service.record_audit_log(user.account_id, user.username, "CREATE_ZONE", "khuvucdo", zone_id, body.model_dump())
    await ws_manager.broadcast("infrastructure_updated")
    return {"id": zone_id}


@app.put("/api/zones/{zone_id}")
async def update_zone(
    zone_id: int,
    body: ZoneRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_zone(zone_id, body.lot_id, body.name)
    await ws_manager.broadcast("infrastructure_updated")
    return {"message": "Đã cập nhật khu vực."}


@app.delete("/api/zones/{zone_id}")
async def delete_zone(
    zone_id: int,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_zone(zone_id)
    await ws_manager.broadcast("infrastructure_updated")
    return {"message": "Đã xóa khu vực."}


@app.get("/api/slots")
def list_slots(
    lot_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    status_filter: Optional[int] = None,
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    slots = service.get_slots(lot_id=lot_id, zone_id=zone_id)
    if status_filter is not None:
        slots = [s for s in slots if int(s["trangthai"]) == status_filter]
    return jsonable_encoder(slots)


@app.post("/api/slots")
async def add_slots(
    body: AddSlotsRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    created = service.add_slots_to_zone(body.zone_id, body.count)
    await ws_manager.broadcast("infrastructure_updated")
    return {"created": created}


@app.patch("/api/slots/{slot_id}/maintenance")
async def set_slot_maintenance(
    slot_id: int,
    body: SlotMaintenanceRequest,
    _user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.set_slot_maintenance(slot_id, body.maintenance)
    await ws_manager.broadcast("slots_updated", {"slot_id": slot_id})
    return {"message": "Đã cập nhật trạng thái vị trí."}


@app.delete("/api/slots/{slot_id}")
async def delete_slot(
    slot_id: int,
    _user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_slot(slot_id)
    await ws_manager.broadcast("slots_updated", {"slot_id": slot_id})
    return {"message": "Đã xóa vị trí đỗ."}


@app.post("/api/slots/reconcile")
async def reconcile_slots(
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.reconcile_slot_states()
    service.record_audit_log(user.account_id, user.username, "RECONCILE_SLOTS", "vitrido")
    await ws_manager.broadcast("slots_updated")
    return {"message": "Đã đồng bộ trạng thái ô đỗ."}


# ------------------------------------------------------------------
# Gate Operations: Check-in / Check-out / Turns
# ------------------------------------------------------------------


@app.get("/api/turns/active")
def list_active_turns(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_active_turns())


@app.post("/api/turns/check-in")
async def check_in(
    body: CheckInRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    emp_id = body.employee_id or user.employee_id
    turn_id = service.check_in_vehicle(
        license_plate=body.license_plate,
        vehicle_type_id=body.vehicle_type_id,
        slot_id=body.slot_id,
        card_id=body.card_id,
        employee_id=emp_id,
    )
    await ws_manager.broadcast("turn_checked_in", {"turn_id": turn_id, "slot_id": body.slot_id})
    return {"turn_id": turn_id}


@app.get("/api/turns/{turn_id}/quote")
def fee_quote(
    turn_id: int,
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    return jsonable_encoder(asdict(service.get_fee_quote(turn_id)))


@app.post("/api/turns/{turn_id}/check-out")
async def check_out(
    turn_id: int,
    body: CheckOutRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    emp_id = body.employee_id or user.employee_id
    quote = service.check_out_vehicle(
        turn_id=turn_id,
        employee_id=emp_id,
        lost_card=body.lost_card,
        lost_card_fee=body.lost_card_fee,
    )
    result = asdict(quote)
    result["payment_method"] = body.payment_method
    if body.lost_card:
        service.record_audit_log(
            user.account_id,
            user.username,
            "CHECKOUT_LOST_CARD",
            "luotdo",
            turn_id,
            result,
        )
    await ws_manager.broadcast("turn_checked_out", {"turn_id": turn_id})
    return jsonable_encoder(result)


@app.post("/api/turns/{turn_id}/move-slot")
async def move_slot(
    turn_id: int,
    body: MoveSlotRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.move_active_turn_slot(turn_id, body.new_slot_id)
    service.record_audit_log(
        user.account_id,
        user.username,
        "MOVE_TURN_SLOT",
        "luotdo",
        turn_id,
        {"new_slot_id": body.new_slot_id},
    )
    await ws_manager.broadcast("slots_updated", {"turn_id": turn_id})
    return {"message": "Đã chuyển vị trí đỗ."}


@app.post("/api/turns/{turn_id}/cancel")
async def cancel_turn(
    turn_id: int,
    user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.cancel_active_turn(turn_id)
    service.record_audit_log(user.account_id, user.username, "CANCEL_TURN", "luotdo", turn_id)
    await ws_manager.broadcast("turn_cancelled", {"turn_id": turn_id})
    return {"message": "Đã hủy lượt gửi xe."}


# ------------------------------------------------------------------
# Transactions & Shifts
# ------------------------------------------------------------------


@app.get("/api/transactions")
def list_transactions(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    vehicle_type_id: Optional[int] = None,
    keyword: Optional[str] = None,
    limit: int = Query(default=300, ge=1, le=2000),
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    rows = service.get_transactions(
        date_from=start_date,
        date_to=end_date,
        vehicle_type_id=vehicle_type_id,
        limit=limit,
    )
    if keyword and keyword.strip():
        q = keyword.strip().lower()
        rows = [
            r
            for r in rows
            if q in str(r.get("bienso") or "").lower()
            or q in str(r.get("mathe") or "").lower()
            or q in str(r.get("nhanvien") or "").lower()
            or q in str(r.get("ma_gd") or "").lower()
        ]
    return jsonable_encoder(rows)


@app.patch("/api/transactions/{payment_id}/status")
def update_transaction_status(
    payment_id: int,
    body: PaymentStatusRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_payment_status(payment_id, body.status)
    service.record_audit_log(
        user.account_id,
        user.username,
        "UPDATE_PAYMENT_STATUS",
        "thanhtoan",
        payment_id,
        {"status": body.status},
    )
    return {"message": "Đã cập nhật trạng thái thanh toán."}


@app.get("/api/shifts/active")
def get_active_shift(
    user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    return jsonable_encoder({"shift": service.get_active_shift(user.employee_id)})


@app.get("/api/shifts")
def list_shifts(
    limit: int = Query(default=50, ge=1, le=200),
    _user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_shifts(limit=limit))


@app.post("/api/shifts/open")
def open_shift(
    body: ShiftOpenRequest,
    user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    shift_id = service.open_shift(
        employee_id=user.employee_id,
        lot_id=body.lot_id or user.lot_id,
        opening_cash=body.opening_cash,
        note=body.note,
    )
    service.record_audit_log(user.account_id, user.username, "OPEN_SHIFT", "ca_lam_viec", shift_id, body.model_dump())
    return {"id": shift_id}


@app.post("/api/shifts/{shift_id}/close")
def close_shift(
    shift_id: int,
    body: ShiftCloseRequest,
    user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    res = service.close_shift(shift_id, user.employee_id, body.actual_cash, body.note)
    service.record_audit_log(user.account_id, user.username, "CLOSE_SHIFT", "ca_lam_viec", shift_id, res)
    return jsonable_encoder(res)


# ------------------------------------------------------------------
# Monthly Passes & Tariffs
# ------------------------------------------------------------------


@app.get("/api/passes")
def list_passes(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_monthly_passes())


@app.get("/api/passes/summary")
def passes_summary(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    return jsonable_encoder(service.get_monthly_pass_revenue_summary())


@app.post("/api/passes")
async def register_pass(
    body: PassRegisterRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    pass_id = service.register_monthly_pass(
        hoten=body.hoten,
        sdt=body.sdt,
        cccd=body.cccd,
        customer_type_id=body.customer_type_id,
        license_plate=body.license_plate,
        vehicle_type_id=body.vehicle_type_id,
        card_id=body.card_id,
        months=body.months,
        employee_id=user.employee_id,
        payment_method=body.payment_method,
    )
    service.record_audit_log(
        user.account_id,
        user.username,
        "REGISTER_PASS",
        "vethang",
        pass_id,
        {"plate": body.license_plate, "months": body.months},
    )
    await ws_manager.broadcast("passes_updated")
    return {"id": pass_id}


@app.post("/api/passes/{pass_id}/renew")
async def renew_pass(
    pass_id: int,
    body: PassRenewRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    res = service.renew_monthly_pass(
        pass_id,
        body.months,
        employee_id=user.employee_id,
        payment_method=body.payment_method,
    )
    service.record_audit_log(user.account_id, user.username, "RENEW_PASS", "vethang", pass_id, res)
    await ws_manager.broadcast("passes_updated")
    return jsonable_encoder(res)


@app.put("/api/passes/{pass_id}/assets")
async def update_pass_assets(
    pass_id: int,
    body: PassAssetsUpdateRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_monthly_pass_assets(pass_id, body.plate, body.vehicle_type_id, body.new_card_id)
    service.record_audit_log(user.account_id, user.username, "UPDATE_PASS_ASSETS", "vethang", pass_id, body.model_dump())
    await ws_manager.broadcast("passes_updated")
    return {"message": "Đã cập nhật xe và thẻ vé tháng."}


@app.delete("/api/passes/{pass_id}")
async def cancel_pass(
    pass_id: int,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.cancel_monthly_pass(pass_id)
    service.record_audit_log(user.account_id, user.username, "CANCEL_PASS", "vethang", pass_id)
    await ws_manager.broadcast("passes_updated")
    return {"message": "Đã hủy vé tháng."}


@app.get("/api/tariffs")
def list_tariffs(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_tariffs())


@app.post("/api/tariffs")
def create_tariff(
    body: TariffCreateRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    tid = service.create_tariff(body.ticket_type, body.vehicle_type_id, body.customer_type_id, body.unit_price)
    service.record_audit_log(user.account_id, user.username, "CREATE_TARIFF", "banggia", tid, body.model_dump())
    return {"id": tid}


@app.put("/api/tariffs/{tariff_id}")
def update_tariff(
    tariff_id: int,
    body: TariffUpdateRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_tariff(tariff_id, body.unit_price)
    service.record_audit_log(user.account_id, user.username, "UPDATE_TARIFF", "banggia", tariff_id, body.model_dump())
    return {"message": "Đã cập nhật đơn giá."}


@app.delete("/api/tariffs/{tariff_id}")
def delete_tariff(
    tariff_id: int,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_tariff(tariff_id)
    service.record_audit_log(user.account_id, user.username, "DELETE_TARIFF", "banggia", tariff_id)
    return {"message": "Đã xóa biểu giá."}


# ------------------------------------------------------------------
# Catalogs: Vehicle Types, Customer Types, People, Cards, Vehicles
# ------------------------------------------------------------------


@app.get("/api/catalogs")
def get_catalogs(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "vehicle_types": service.get_vehicle_types(),
            "customer_types": service.get_customer_types(),
            "lots": service.get_parking_lots(),
            "employees": service.get_employees(),
        }
    )


@app.get("/api/people/employees")
def list_employees(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_employees_detail())


@app.post("/api/people/employees")
def create_employee(
    body: EmployeeRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    eid = service.create_employee(
        hoten=body.hoten,
        chucvu=body.chucvu,
        sdt=body.sdt,
        email=body.email,
        diachi=body.diachi,
        cccd=body.cccd,
        lot_id=body.lot_id,
    )
    service.record_audit_log(user.account_id, user.username, "CREATE_EMPLOYEE", "nhanvien", eid, {"hoten": body.hoten})
    return {"id": eid}


@app.put("/api/people/employees/{emp_id}")
def update_employee(
    emp_id: int,
    body: EmployeeRequest,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_employee(
        emp_id=emp_id,
        hoten=body.hoten,
        chucvu=body.chucvu,
        sdt=body.sdt,
        email=body.email,
        diachi=body.diachi,
        cccd=body.cccd,
        lot_id=body.lot_id,
    )
    return {"message": "Đã cập nhật nhân viên."}


@app.delete("/api/people/employees/{emp_id}")
def delete_employee(
    emp_id: int,
    user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_employee(emp_id)
    service.record_audit_log(user.account_id, user.username, "DELETE_EMPLOYEE", "nhanvien", emp_id)
    return {"message": "Đã xóa nhân viên."}


@app.get("/api/people/customers")
def list_customers(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_customers_detail())


@app.put("/api/people/customers/{customer_id}")
def update_customer(
    customer_id: int,
    body: CustomerUpdateRequest,
    _user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_customer(customer_id, body.hoten, body.sdt, body.cccd, body.customer_type_id)
    return {"message": "Đã cập nhật khách hàng."}


@app.delete("/api/people/customers/{customer_id}")
def delete_customer(
    customer_id: int,
    _user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_customer(customer_id)
    return {"message": "Đã xóa khách hàng."}


@app.get("/api/people/walkins")
def list_walkins(
    limit: int = Query(default=200, ge=1, le=1000),
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_walkin_visitors(limit=limit))


@app.get("/api/cards")
def list_cards(
    only_available: bool = False,
    detail: bool = False,
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    if detail:
        return jsonable_encoder(service.get_cards_detail())
    return jsonable_encoder(service.get_cards(only_available=only_available))


@app.post("/api/cards")
def create_card(
    body: CardCreateRequest,
    _user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    cid = service.create_card(body.code)
    return {"id": cid}


@app.patch("/api/cards/{card_id}/status")
def set_card_status(
    card_id: int,
    body: CardStatusRequest,
    user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.set_card_status(card_id, body.status)
    service.record_audit_log(user.account_id, user.username, "SET_CARD_STATUS", "thexe", card_id, body.model_dump())
    return {"message": "Đã cập nhật trạng thái thẻ."}


@app.delete("/api/cards/{card_id}")
def delete_card(
    card_id: int,
    _user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_card(card_id)
    return {"message": "Đã xóa thẻ xe."}


@app.get("/api/vehicles")
def list_vehicles(
    _user: AuthUser = Depends(get_current_user),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_vehicles_detail())


@app.put("/api/vehicles/{vehicle_id}")
def update_vehicle(
    vehicle_id: int,
    body: VehicleUpdateRequest,
    _user: AuthUser = Depends(require_roles("ADMIN", "OPERATOR")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.update_vehicle(vehicle_id, body.plate, body.vehicle_type_id)
    return {"message": "Đã cập nhật phương tiện."}


@app.delete("/api/vehicles/{vehicle_id}")
def delete_vehicle(
    vehicle_id: int,
    _user: AuthUser = Depends(require_roles("ADMIN")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, str]:
    service.delete_vehicle(vehicle_id)
    return {"message": "Đã xóa phương tiện."}


# ------------------------------------------------------------------
# Analytics & Audit Logs
# ------------------------------------------------------------------


@app.get("/api/analytics/summary")
def analytics_summary(
    days: int = Query(default=30, ge=7, le=365),
    _user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> dict[str, Any]:
    return jsonable_encoder(
        {
            "daily": service.get_daily_revenue(days=days),
            "by_vehicle_type": service.get_revenue_by_vehicle_type(),
            "by_lot": service.get_revenue_by_lot(),
            "pass_summary": service.get_monthly_pass_revenue_summary(),
        }
    )


@app.get("/api/audit-logs")
def get_audit_logs(
    limit: int = Query(default=100, ge=1, le=500),
    _user: AuthUser = Depends(require_roles("ADMIN", "ACCOUNTANT")),
    service: ParkingService = Depends(get_parking_service),
) -> list[dict[str, Any]]:
    return jsonable_encoder(service.get_audit_logs(limit=limit))


# Mount built frontend SPA in production if present
_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"
if _FRONTEND_DIST.exists():
    app.mount("/", StaticFiles(directory=str(_FRONTEND_DIST), html=True), name="frontend")
