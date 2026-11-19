from dataclasses import dataclass
from typing import Optional

@dataclass
class KhachHang:
    id: Optional[int] = None
    hoten: Optional[str] = None
    sdt: str = ""
    cccd: str = ""
    idlkh: Optional[int] = None
