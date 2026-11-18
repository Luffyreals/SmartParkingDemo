from dataclasses import dataclass
from typing import Optional

@dataclass
class BangGia:
    id: Optional[int] = None
    loaive: Optional[str] = None
    dongia: Optional[int] = None
    idlpt: Optional[int] = None
    idlkh: Optional[int] = None
