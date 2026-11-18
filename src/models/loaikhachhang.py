from dataclasses import dataclass
from typing import Optional

@dataclass
class LoaiKhachHang:
    id: Optional[int] = None
    tenloai: Optional[str] = None
