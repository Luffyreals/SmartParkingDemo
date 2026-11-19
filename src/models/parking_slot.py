from dataclasses import dataclass

@dataclass
class ParkingSlot:
    id: int
    idkvd: int  # Foreign key to khuvucdo
    sothutu: int
    trangthai: int  # 1: Trống, 0: Đang đỗ, 2: Bảo trì
