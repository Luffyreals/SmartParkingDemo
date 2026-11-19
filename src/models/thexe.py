from dataclasses import dataclass
from typing import Optional

@dataclass
class TheXe:
    id: Optional[int] = None
    maso: Optional[str] = None
    trangthai: Optional[int] = None  # 0: Đang dùng, 1: Sẵn sàng, 2: Mất/Hỏng
