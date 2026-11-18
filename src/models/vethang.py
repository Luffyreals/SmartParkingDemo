from dataclasses import dataclass
from typing import Optional

@dataclass
class VeThang:
    id: Optional[int] = None
    ngaybatdau: Optional[str] = None
    ngayketthuc: Optional[str] = None
    idtx: Optional[int] = None
    idpt: Optional[int] = None
    idbg: Optional[int] = None
    idkh: Optional[int] = None
