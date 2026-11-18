from dataclasses import dataclass

@dataclass
class ParkingSlot:
    id: int
    idkvd: int  # Foreign key to khuvucdo
    sothutu: int
    trangthai: bool # 1: Active/Occupied, 0: Available/Inactive (mapping TinyInt)
