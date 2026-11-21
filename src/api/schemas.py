from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class ChangePasswordRequest(BaseModel):
    old_password: str
    new_password: str


class AccountCreateRequest(BaseModel):
    employee_id: int
    username: str
    password: str
    role: str = "OPERATOR"


class AccountUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    new_password: Optional[str] = None


class CheckInRequest(BaseModel):
    license_plate: str
    vehicle_type_id: int
    slot_id: int
    card_id: int
    employee_id: Optional[int] = None


class CheckOutRequest(BaseModel):
    employee_id: Optional[int] = None
    payment_method: str = "Tiền mặt"
    lost_card: bool = False
    lost_card_fee: int = 0


class MoveSlotRequest(BaseModel):
    new_slot_id: int


class PaymentStatusRequest(BaseModel):
    status: str


class LotRequest(BaseModel):
    name: str
    location: str


class ZoneRequest(BaseModel):
    lot_id: int
    name: str


class AddSlotsRequest(BaseModel):
    zone_id: int
    count: int = Field(ge=1, le=50)


class SlotMaintenanceRequest(BaseModel):
    maintenance: bool


class TariffCreateRequest(BaseModel):
    ticket_type: str
    vehicle_type_id: int
    customer_type_id: int
    unit_price: int


class TariffUpdateRequest(BaseModel):
    unit_price: int


class PassRegisterRequest(BaseModel):
    hoten: str
    sdt: str
    cccd: str
    customer_type_id: int
    license_plate: str
    vehicle_type_id: int
    card_id: int
    months: int = 1
    payment_method: str = "Tiền mặt"


class PassRenewRequest(BaseModel):
    months: int = 1
    payment_method: str = "Tiền mặt"


class PassAssetsUpdateRequest(BaseModel):
    plate: str
    vehicle_type_id: int
    new_card_id: int


class EmployeeRequest(BaseModel):
    hoten: str
    chucvu: str
    sdt: str
    email: str = ""
    diachi: str = ""
    cccd: str = ""
    lot_id: Optional[int] = None


class CustomerUpdateRequest(BaseModel):
    hoten: str
    sdt: str
    cccd: str
    customer_type_id: int


class CardCreateRequest(BaseModel):
    code: str


class CardStatusRequest(BaseModel):
    status: int


class VehicleUpdateRequest(BaseModel):
    plate: str
    vehicle_type_id: int


class ShiftOpenRequest(BaseModel):
    lot_id: Optional[int] = None
    opening_cash: int = 0
    note: str = ""


class ShiftCloseRequest(BaseModel):
    actual_cash: int
    note: str = ""
