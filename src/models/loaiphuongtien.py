from dataclasses import dataclass
from typing import Optional

@dataclass
class LoaiPhuongTien:
    id: Optional[int] = None
    tenloai: Optional[str] = None
