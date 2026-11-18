from dataclasses import dataclass
from typing import Optional

@dataclass
class PhuongTien:
    id: Optional[int] = None
    bienso: Optional[str] = None
    idlpt: Optional[int] = None
