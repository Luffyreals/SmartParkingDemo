from dataclasses import dataclass

@dataclass
class Vehicle:
    id: int
    bienso: str
    idlpt: int  # Foreign key to loaiphuongtien
