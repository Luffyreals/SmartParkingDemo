from dataclasses import dataclass
from typing import Optional

@dataclass
class KhachHang:
    id: Optional[int] = None
    hoten: str = ""
    sdt: str = ""
    cccd: str = ""
    idlkh: Optional[int] = None
